from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import matplotlib.pyplot as plt

from gangLogger.myLog import MyLog
from gangUtils.generalUtils import GeneralUtils
from spectralClusterConst import *
import matplotlib.colors as colors

class DataSave(QObject):
    logger = MyLog('SaveData', BASEDIR)
    run_end = pyqtSignal()

    def __init__(self, *args):
        super().__init__()
        self.conductance, self.distance, self.length_arr,self.additional_length,self.labels, self.cluster_num, self.keyPara = args
    def run(self):
        try:
            save_path = self.keyPara['SAVE_FOLDER_PATH']
            labels = self.labels
            for i in range(self.cluster_num):
                sub_path = os.path.join(save_path, f'cluster{i+1}')
                index_i = np.where(labels == i)[0]
                Cluster_i_cond = self.conductance[index_i].reshape(-1)
                Cluster_i_dist = self.distance[index_i].reshape(-1)
                H_1D_cond, bins_1D_edges = np.histogram(Cluster_i_cond, bins=1100, range=[-10, 1])
                H_2D_cond, _, _ = np.histogram2d(Cluster_i_dist, Cluster_i_cond, bins=[500, 1000],
                                                            range=[[-0.5, 3], [-10, 1]])
                np.savetxt(os.path.join(sub_path, '2dHist.txt'), H_2D_cond * 2, fmt='%d', delimiter='\t')
                hist_1D_cond = np.array([bins_1D_edges[:-1], H_1D_cond]).T
                np.savetxt(os.path.join(sub_path, 'logHist.txt'), hist_1D_cond, fmt='%.5e', delimiter='\t')
                data = np.array([Cluster_i_dist, Cluster_i_cond]).T
                np.savetxt(os.path.join(sub_path, 'goodtrace.txt'), data, fmt='%.5e', delimiter='\t')
                _1D_LENG_XLEFT = self.keyPara["le_1D_len_Xleft"]
                _1D_LENG_XRIGHT = self.keyPara["le_1D_len_Xright"]
                _1D_LENG_BINS = int(self.keyPara["le_1D_len_Bins"])
                length = self.length_arr[index_i]
                H_1D_length, bins_1D_length_edges = np.histogram(length, bins=_1D_LENG_BINS,
                                                         range=[_1D_LENG_XLEFT, _1D_LENG_XRIGHT])
                hist_1D_length = np.array([bins_1D_length_edges[:-1], H_1D_length]).T
                np.savetxt(os.path.join(sub_path, 'plateau.txt'), hist_1D_length, fmt='%.5e', delimiter='\t')
                np.savez(os.path.join(sub_path, 'single_trace.npz'), distance_array=self.distance[index_i], 
                         conductance_array = self.conductance[index_i], length_array=length, additional_length=self.additional_length)
            self.saveFig()
            self.run_end.emit()
        except Exception as e:
            errMsg = f"据保存异常：{e}"
            self.logger.error(errMsg)
    
    def saveFig(self):
        print("save fig ...")
        def makeBar(rgbTest, colorName='my_color'):

            r1 = np.linspace(rgbTest[0], 255, 128)
            r2 = np.linspace(rgbTest[1], 255, 128)
            r3 = np.linspace(rgbTest[2], 255, 128)

            rgbTest2 = np.vstack((r1, r2, r3))
            icmapTest = colors.ListedColormap(rgbTest2.T[::-1] / 255, name=colorName)
            return icmapTest
        save_path = self.keyPara['SAVE_FOLDER_PATH']
        colorSet = np.array([106, 165, 171,
                             246, 138, 65,
                             26, 70, 105,
                             206, 190, 175,
                             157, 89, 130,
                             242, 174, 65,
                             61, 68, 78,
                             230, 81, 77])
        colorSetTest = colorSet.reshape(-1, 3) / 255
        colorBarCmap = []
        for rgb in colorSet.reshape(-1, 3):
            colorCmap = makeBar(rgb)
            colorBarCmap.append(colorCmap)
        condHigh, condLow = self.keyPara["le_1DCluster_LogG_High"], self.keyPara["le_1DCluster_LogG_Low"]
        _2DCluster_BINSX = int(self.keyPara["le_2DCluster_Cloud_BinsX"])
        _2DCluster_BINSY = int(self.keyPara["le_2DCluster_Cloud_BinsY"])
        _2DCluster_XLEFT = self.keyPara["le_2DCluster_Cloud_Xleft"]
        _2DCluster_XRIGHT = self.keyPara["le_2DCluster_Cloud_Xright"]
        _2DCluster_YLEFT = self.keyPara["le_2DCluster_Cloud_Yleft"]
        _2DCluster_YRIGHT = self.keyPara["le_2DCluster_Cloud_Yright"]
        _2DCluster_VMIN = self.keyPara["le_2DCluster_Cloud_VMin"]
        _2DCluster_VMAX = self.keyPara["le_2DCluster_Cloud_VMax"]
        FONTSIZE=8
        fig = plt.figure(figsize=(10, 10))
        labels = self.labels
        for i in range(self.cluster_num):
            sub_path = os.path.join(save_path, f'cluster{i+1}')
            index_i = np.where(labels == i)[0]
            Cluster_i_cond = self.conductance[index_i].reshape(-1)
            Cluster_i_dist = self.distance[index_i].reshape(-1)
            plt.cla()
            plt.hist(Cluster_i_cond, bins=300, color='green', range=(condLow, condHigh), histtype='stepfilled', alpha=0.8)
            plt.title(f'Cluster{i+1}: {len(index_i)}')
            plt.xlabel('Conductance', fontsize=FONTSIZE)
            plt.ylabel('Counts', fontsize=FONTSIZE)
            plt.ticklabel_format(style='scientific', scilimits=(0, 2), useMathText=True)
            plt.xlim(condLow, condHigh)
            fig.savefig(os.path.join(sub_path, 'hist.png'), dpi=300)
            plt.cla()
            
            plt.hist2d(
                Cluster_i_dist, Cluster_i_cond,
                bins=[_2DCluster_BINSX, _2DCluster_BINSY],
                range=[[_2DCluster_XLEFT, _2DCluster_XRIGHT],
                       [_2DCluster_YLEFT, _2DCluster_YRIGHT]],
                vmin=_2DCluster_VMIN,
                vmax=_2DCluster_VMAX,
                cmap=colorBarCmap[i % len(colorBarCmap)],
            )
            plt.title(f'Cluster {i + 1}')
            plt.xlabel("Length/nm")
            plt.ylabel("Conductance/log(G/G$_0$)")
            plt.savefig(os.path.join(sub_path, 'hist2d.png'), dpi=300)
        
