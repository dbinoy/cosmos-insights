from sqlalchemy import create_engine

driver = 'ODBC+Driver+18+for+SQL+Server'
workspace = 'lakehouse-dev-ws-ondemand'
username = 'synapseadmin'
password = 'Rec0reR0ck$'
training_database = 'training_ldw'
training_engine = create_engine(f'mssql+pyodbc://{username}:{password}@{workspace}.sql.azuresynapse.net:1433/{training_database}?driver={driver}')
workflow_database = 'workflow_ldw'
workflow_engine = create_engine(f'mssql+pyodbc://{username}:{password}@{workspace}.sql.azuresynapse.net:1433/{workflow_database}?driver={driver}')
compliance_database = 'compliance_ldw'
compliance_engine = create_engine(f'mssql+pyodbc://{username}:{password}@{workspace}.sql.azuresynapse.net:1433/{compliance_database}?driver={driver}')