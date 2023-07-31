from sklearn.cluster import KMeans

import numpy as np

from typing import Dict

def diversity_selection(embedding_dict: Dict, batch_size: int):
    """Select the most diverse samples from the given embedding dict using K-Means clustering"""
    # Perform K-Means and select the most diverse samples

    # Convert the embedding dict to a list
    X_train = np.array([vector.numpy() for vector in embedding_dict.values()])

    kmeans = KMeans(n_clusters=batch_size)

    # Fit the model to the data
    kmeans.fit(X_train)

    # Find the closest points to the cluster centers
    closest_points = kmeans.transform(X_train).argmin(axis=0)

    doi_list = []

    for index, doi in enumerate(embedding_dict.keys()):
        if index in closest_points:
            doi_list.append(doi)

    return doi_list
