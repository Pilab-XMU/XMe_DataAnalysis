# -*- coding: utf-8 -*-
# @Time   : 2021/11/10 14:54
# @Author : Gang
# @File   : spectralClusterDataProcessUtils.py
import numpy as np
from gangLogger.myLog import MyLog
from spectralClusterConst import *
from sklearn import cluster
import sklearn.metrics.pairwise as skmp


class SpectralClusterDataProcessUtils:
    logger = MyLog("SpectralClusterDataProcessUtils", BASEDIR)

    @classmethod
    def loadData(cls, keyPara):
        """
        数据加载
        :param keyPara:
        :return:
        """
        filePath = keyPara["FILE_PATH"]
        dataset = np.load(filePath)
        conductance, distance, length_arr = dataset["conductance_array"], dataset["distance_array"], dataset['length_array']
        return conductance, distance, length_arr, dataset['additional_length']

    @classmethod
    def getHist1D(cls, keyPara, conductance):
        NumTraces = conductance.shape[0]
        condHigh, condLow = keyPara["le_Hist_LogG_High"], keyPara["le_Hist_LogG_Low"]
        bins = int(keyPara["le_Hist_Bins"])
        dataHistAll = np.zeros((NumTraces, bins))  ###save the all traces' histogram....

        binEdges = None
        for i in range(NumTraces):
            hist, binEdges = np.histogram(conductance[i, :], bins, range=[condLow, condHigh], density=False)
            if max(hist) != 0:
                dataHistAll[i, :] = hist

        dataHistAll_X = binEdges[1:] - (binEdges[1] - binEdges[0]) / 2
        return dataHistAll, dataHistAll_X

    @classmethod
    def clusterWithSP(cls, keyPara, dataHistAll, dataHistAll_X):
        ClusterNMax = int(keyPara["le_ClusterNumMax"])
        condHigh, condLow = keyPara["le_Cluster_LogG_High"], keyPara["le_Cluster_LogG_Low"]

        trueIndex = np.where((dataHistAll_X >= condLow) & (dataHistAll_X <= condHigh))[0]
        dataHistAllSelect = dataHistAll[:, trueIndex]

        histCorrcoef = np.corrcoef(dataHistAllSelect)
        histCorrcoef[np.isnan(histCorrcoef)] = 0
        histCorrcoefNorm = histCorrcoef * 0.5 + 0.5

        labelsList = []

        for nCl in range(2, ClusterNMax + 1):
            spectralFun = cluster.SpectralClustering(n_clusters=nCl, random_state=429,
                                                     n_jobs=-1, affinity='precomputed')
            spectralFun.fit(histCorrcoefNorm)
            labels = spectralFun.labels_
            labelsList.append(labels)
        return labelsList, dataHistAllSelect

    @classmethod
    def getCHI(cls, keyPara, labelsList, dataHistAllSelect):
        metric = keyPara["cmb_Metric"]
        numClusters = len(labelsList)
        calinskiHarabaszIndex = np.ndarray(numClusters)
        for i in range(numClusters):
            calinskiHarabaszIndex[i] = cls.calinskiHarabaszScoreM(dataHistAllSelect, labelsList[i], metric)
        return calinskiHarabaszIndex

    @classmethod
    def calinskiHarabaszScoreM(cls, X, labels, metric):
        ####where a higher Calinski-Harabasz score relates to a model with better defined clusters.
        """Compute the Calinski and Harabasz score.
        It is also known as the Variance Ratio Criterion.
        The score is defined as ratio between the within-cluster dispersion and
        the between-cluster dispersion.
        Read more in the :ref:`User Guide <calinski_harabasz_index>`.
        Parameters
        ----------
        X : array-like, shape (``n_samples``, ``n_features``)
            List of ``n_features``-dimensional data points. Each row corresponds
            to a single data point.
        labels : array-like, shape (``n_samples``,)
            Predicted labels for each sample.
        Returns
        -------
        score : float
            The resulting Calinski-Harabasz score.
        References
        ----------
        .. [1] `T. Calinski and J. Harabasz, 1974. "A dendrite method for cluster
           analysis". Communications in Statistics
           <https://www.tandfonline.com/doi/abs/10.1080/03610927408827101>`_
        """

        if metric == 'correlation':
            zerosRows = np.where(np.all(X == 0, axis=1))
            X = np.delete(X, zerosRows, axis=0)
            labels = np.delete(labels, zerosRows)

        NSamples, _ = X.shape
        NLabels = len(set(labels))

        extraDisp, intraDisp = 0., 0.

        mean = np.mean(X, axis=0)

        for k in range(NLabels):
            clusterK = X[labels == k]  ####cluster
            meanK = np.mean(clusterK, axis=0)
            extraDisp += len(clusterK) * (skmp.pairwise_distances(np.array(meanK, ndmin=2),
                                                                  np.array(mean, ndmin=2),
                                                                  metric=metric, n_jobs=-1) ** 2)[0][0]

            intraDisp += np.sum(skmp.pairwise_distances(clusterK,
                                                        np.array(meanK, ndmin=2),
                                                        metric=metric, n_jobs=-1) ** 2)
        return (1. if intraDisp == 0. else
                extraDisp * (NSamples - NLabels) /
                (intraDisp * (NLabels - 1.)))
