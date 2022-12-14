import numpy as np
import pandas as pd
import matplotlib as matplotlib
import matplotlib.pyplot as plt
import math
import time
# !pip install shapely
# !pip install geographiclib
import shapely
from shapely.geometry import Polygon, LineString, Point
import geographiclib
from geographiclib.geodesic import Geodesic
import Parameters


def create_graph():
    graph = "graphe_{}".format(int(h/60))
    query = "CALL gds.graph.create('{}',".format(graph)
    query += " '*', '*',{relationshipProperties: 'inter_time'})"
    execute(driver, query)
    
def delete_graph(h_min):
    graph = "graphe_{}".format(h_min)
    query = "CALL gds.graph.drop('{}')".format(graph)
    execute(driver, query)

def get_stations_df():
    stations0 = []
    for i in range(len(stops)):
        stations0.append(Point(stops.stop_lon[i], stops.stop_lat[i]))
    stations = pd.DataFrame()
    stations['stop_id'] = stops.stop_id
    stations['station'] = [i for i in stations0]
    return stations

# Plots
def choose(id_station, show, show_choose): 
    station = stations.iloc[np.where(stations.stop_id == id_station)[0][0]]
    A = Point(station.station.x, station.station.y)
    L = Point(A.x - 0.051408, A.y)
    R = Point(A.x + 0.051408, A.y)
    U = Point(A.x, A.y + 0.01799425)
    D = Point(A.x, A.y - 0.01799431)
    UL = Point(L.x,U.y)
    DL = Point(L.x,D.y)
    UR = Point(R.x,U.y)
    DR = Point(R.x,D.y)
    centroids_left = pos_centroids.iloc[np.where((pos_centroids.longitude > L.x) & (pos_centroids.longitude < A.x) & (pos_centroids.latitude < U.y) & (pos_centroids.latitude > D.y))]
    centroids_right = pos_centroids.iloc[np.where((pos_centroids.longitude < R.x) & (pos_centroids.longitude > A.x) & (pos_centroids.latitude < U.y) & (pos_centroids.latitude > D.y))]
    if show == True:
        fig, ax = plt.subplots()
        ax.scatter([L.x,R.x,U.x,D.x,UL.x,DL.x,UR.x,DR.x], [L.y,R.y,U.y,D.y,UL.y,DL.y,UR.y,DR.y])
        ax.annotate('L', (L.x,L.y))
        ax.annotate('R', (R.x,R.y))
        ax.annotate('U', (U.x,U.y))
        ax.annotate('D', (D.x,D.y))
        ax.annotate('UL', (UL.x,UL.y))
        ax.annotate('DL', (DL.x,DL.y))
        ax.annotate('UR', (UR.x,UR.y))
        ax.annotate('DR', (DR.x,DR.y))
        ax.scatter([centroids_left.longitude.iloc[i] for i in range(len(centroids_left))], [centroids_left.latitude.iloc[i] for i in range(len(centroids_left))])
        ax.scatter([centroids_right.longitude.iloc[i] for i in range(len(centroids_right))], [centroids_right.latitude.iloc[i] for i in range(len(centroids_right))])
        ax.scatter(A.x, A.y)
        ax.annotate("'{}'".format(id_station), (A.x - 0.003, A.y-0.003))
        ax.legend(loc = (1.01,0.78), labels = ('limites','centroides ?? gauche','centroides ?? droite'))
        ax.set_title("Station '{}'.format(id_station", fontsize = 14)
        print("Distances avec la station '{}' :".format(id_station))
        [print(j,geod.Inverse(A.y,A.x,i.y,i.x)['s12']) for i,j in zip([L,R,U,D,UL,DL,UR,DR],['L','R','U','D','UL','DL','UR','DR'])]
        print('\n')
    return centroids_left, centroids_right


def show_choose(station_list):
    plt.scatter([stations.iloc[i].station.x for i in range(len(stations))],[stations.iloc[i].station.y for i in range(len(stations))], c = 'silver')
    for i in station_list:
        station = stations.iloc[np.where(stations.stop_id == i)[0][0]]
        plt.scatter(station.station.x, station.station.y, c = 'black')
    plt.title("Stations")
    plt.xlabel("Longitude", fontsize = 16)
    plt.ylabel("Latitude", fontsize = 16)
    plt.show()
    #plt.savefig(r".\Results\Stations.svg", format = 'svg') 

# DRT
def pax(densite, longueur, largeur, h):
    return 2*densite*longueur*largeur*h

def dist_cycle(longueur, largeur, nb_pax): # m??tres
    return 2*(longueur)*(nb_pax/(nb_pax+1)) + nb_pax*(largeur/3)+(largeur/2)

def temps_cycle(cycle, vitesse, nb_pax): # secondes
    return cycle/vitesse + 60*nb_pax + 120
    
def M(temps_cycle, h):
    return temps_cycle/h

# Neo4j
import neo4j
from neo4j import GraphDatabase

URI = "bolt://127.0.0.1:7687"
USER = "neo4j"
PASSWORD = "123"
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def execute(driver, query):
    """Execute a query."""
    with driver.session() as session:
        if len(query) > 0:
            result = session.run(query)
            return result
        
def get_res(driver, query):
    """Execute a query."""
    with driver.session() as session:
        if len(query) > 0:
            result = session.run(query)
        return [dict(i) for i in result]
    
def create(stop_id):
    print(stop_id, ':')
    left, _ = choose(stop_id, show = False, show_choose = True)
    df_centroids = pd.DataFrame()
    df_centroids['centroid_id'] = left.centroid_id
    df_centroids['longitude'] = left.longitude
    df_centroids['latitude'] = left.latitude
    df_centroids['centroid_id'].to_csv(r".\Stations\id_centroid_station_{}.txt".format(stop_id), index = False)
    for c in df_centroids.centroid_id.iloc:
        query = "MATCH (c:Centroid), (st:Stoptime) WHERE st.stop_id = {} AND c.centroid_id = {} ".format(stop_id,c)
        query += "AND st.departure_duration >= c.departure_duration + {} \n".format(drt_time + waiting_drt)    
        query += "WITH min(st.departure_duration) AS min_dep, c AS c "
        query += "MATCH (c), (st:Stoptime) WHERE st.stop_id = {} AND st.departure_duration = min_dep \n".format(stop_id)
        query += "CREATE (c)-[r:DRT]->(st) SET r.inter_time = st.departure_duration - c.departure_duration SET r.travel_time = {} SET r.waiting_time = {} SET r.pax = {}".format(drt_time, waiting_drt, n)
        execute(driver,query)
    print("Nombre de relations ?? cr??er :", len(df_centroids))
    query = "MATCH ()-[r:DRT]->(st:Stoptime) WHERE st.stop_id = {} RETURN COUNT(r) AS nb".format(stop_id)
    nb_rel_DRT = get_res(driver,query)[0]['nb']
    print("Nombre de relations cr??es :", nb_rel_DRT)
###############################################################################
stops = pd.read_csv(r".\Data\stops.txt")
pos_centroids = pd.read_csv(r".\Data\pos_centroids.txt")
stations = get_stations_df()


start_time = time.time()

# DRT
print("Infos DRT : \n")
densite = Parameters.densite/1000000/3600
longueur = Parameters.longueur
largeur = Parameters.largeur
v = Parameters.vitesse_DRT*1000/3600
h = Parameters.h
n = pax(densite, longueur, largeur, h)
cycle = dist_cycle(longueur, largeur, n)
tmps = temps_cycle(cycle, v, n)
m = M(tmps, h)
waiting_drt = h/2
drt_time = tmps/2
print('h = : ', h/60)
print('Nb pax : ', n)
print('Distance cycle : ', cycle)
print('Distance cycle : ', cycle)
print('Nombre de vehicule :', m)
print('Attente drt : ', waiting_drt)
print('\n Temps de trajet DRT :')
print(drt_time, 'secondes')
print(drt_time/60, 'minutes')
print(drt_time/3600, 'heures')
print('ok \n')

liste_stations = Parameters.liste_stations_DRT
liste_stat = pd.DataFrame()
liste_stat['station_list'] = liste_stations
liste_stat.to_csv(r'.\Stations\list_station_id.txt', index = False)
stat = pd.read_csv(r'.\Stations\list_station_id.txt')
station_list = np.sort([i for i in liste_stations])

show_choose(station_list)

query = "MATCH ()-[r:DRT]-() DELETE r"
execute(driver, query)

ids_centroids = []
for i in station_list:
    print("Station :", i)
    create(i)
    ids_centr = pd.read_csv(r".\Stations\id_centroid_station_{}.txt".format(i)).centroid_id.values
    for j in ids_centr:
        ids_centroids.append(j)
df_centr_ids = pd.DataFrame()
df_centr_ids['centroid_id'] = np.unique(ids_centroids)
df_centr_ids.to_csv(r'.\Results\ids.txt', index = False)
    
# create_graph()

end_time = time.time()
print("temps d'ex??cution :", end_time - start_time)
print((end_time - start_time)/60, 'minutes')
