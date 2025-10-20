import time
import pandas as pd
import concurrent.futures
from sqlalchemy import create_engine

driver = 'ODBC+Driver+18+for+SQL+Server'
workspace = 'lakehouse-dev-ws-ondemand'
username = 'synapseadmin'
password = 'Rec0reR0ck$'
database = 'training_ldw'
engine = create_engine(f'mssql+pyodbc://{username}:{password}@{workspace}.sql.azuresynapse.net:1433/{database}?driver={driver}')

def run_query(item):
    key, query = item
    df = pd.read_sql_query(query, engine)
    return key, df

def run_queries(queries, workers = 5):
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = dict(executor.map(run_query, queries.items()))
    response = {}
    for key in queries.keys():
        response[key] = results[key]    
    return response

if __name__ == "__main__":
    q_aors ='SELECT DISTINCT [AorID], [AorName], [AorShortName] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName]'
    q_offices = 'SELECT DISTINCT [AorShortName], [OfficeCode] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName], [OfficeCode]'
    q_classes = 'SELECT [TopicId],[TopicName],[ClassId],[ClassName],[AorShortName],[StartTime],[InstructorId],[InstructorName],[LocationId],[LocationName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName], [ClassName], [StartTime]'
    q_topics = 'SELECT DISTINCT [TopicId], [TopicName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName]'
    q_instructors = 'SELECT [InstructorID], [Name] FROM [consumable].[Dim_Instructors] ORDER BY [Name]'
    q_locations = 'SELECT [LocationID], [Name] FROM [consumable].[Dim_Locations] ORDER BY [Name]'
    q_request_stats = 'SELECT [TrainingTopicId],[TrainingTopicName],[AorShortName],[AorName],[MemberOffice],[MembersRequested],[TotalRequests] FROM [consumable].[Fact_RequestStats]'
    q_attendance_stats = 'SELECT [TrainingClassId],[ClassName],[TrainingTopicId],[TrainingTopicName],[LocationId],[LocationName],[InstructorId],[InstructorName],[AorShortName],[MemberOffice],[MembersAttended],[TotalAttendances] FROM [consumable].[Fact_AttendanceStats]'

    queries = {
        "aors": q_aors,
        "offices": q_offices,
        "classes": q_classes,
        "topics": q_topics,
        "instructors": q_instructors,
        "locations": q_locations,
        "request_stats": q_request_stats,
        "attendance_stats": q_attendance_stats
    }           

    start = time.time()
    results = run_queries(queries, len(queries.keys()))    
    print("Data Load done in", time.time()-start, "s")
    print("AORs:", results['aors'].shape)
    print("Offices:", results['offices'].shape)
    print("Classes:", results['classes'].shape)
    print("Topics:", results['topics'].shape)
    print("Instructors:", results['instructors'].shape)
    print("Locations:", results['locations'].shape)
    print("Request Stats:", results['request_stats'].shape)
    print("Attendance Stats:", results['attendance_stats'].shape)