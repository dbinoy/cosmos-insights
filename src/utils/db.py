import pandas as pd
import concurrent.futures
from src.config.db import engine
from src.utils.cache import cache


@cache.memoize()
def run_query(key, query):
    df = pd.read_sql_query(query, engine)
    return key, df


def run_queries(queries, workers = 5):
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for k, q in queries.items():
            futures.append(executor.submit(run_query, k, q))
        results = {}
        for fut in concurrent.futures.as_completed(futures):
            key, df = fut.result()
            results[key] = df
    response = {}
    for key in queries.keys():
        response[key] = results[key]
    return response
