from sqlalchemy import create_engine

driver = 'ODBC+Driver+18+for+SQL+Server'
workspace = 'lakehouse-dev-ws-ondemand'
username = 'synapseadmin'
password = 'Rec0reR0ck$'
database = 'recore_ldw'
engine = create_engine(f'mssql+pyodbc://{username}:{password}@{workspace}.sql.azuresynapse.net:1433/{database}?driver={driver}')
