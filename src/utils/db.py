import pandas as pd
import concurrent.futures
from src.config.db import training_engine, workflow_engine, compliance_engine

from src.utils.cache import cache


@cache.memoize()
def run_training_query(key, query):
    df = pd.read_sql_query(query, training_engine)
    return key, df

@cache.memoize()
def run_workflow_query(key, query):
    df = pd.read_sql_query(query, workflow_engine)
    return key, df

@cache.memoize()
def run_compliance_query(key, query):
    df = pd.read_sql_query(query, compliance_engine)
    return key, df
    
def run_queries(queries, database, workers = 5):
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for k, q in queries.items():
            if 'train' in database.lower():
                futures.append(executor.submit(run_training_query, k, q))
            elif 'work' in database.lower():
                futures.append(executor.submit(run_workflow_query, k, q))
            elif 'comp' in database.lower():
                futures.append(executor.submit(run_compliance_query, k, q))
        results = {}
        for fut in concurrent.futures.as_completed(futures):
            key, df = fut.result()
            results[key] = df
    response = {}
    for key in queries.keys():
        response[key] = results[key]
    return response
