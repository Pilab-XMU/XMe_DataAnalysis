import time, os
import numpy as np
from nptdms import TdmsFile
import multiprocessing as mp
from PyQt5.QtCore import QObject, pyqtSignal

from ElectrochemConst import BASEDIR
from gangLogger.myLog import MyLog


def loadTDMSFile(file_path):
    with TdmsFile.open(file_path) as tdms_file:
        group = tdms_file.groups()[0]
        data_v = group.channels()[0][:] 
        data_c = group.channels()[1][:]
    return data_v, data_c

def cut(V, logG, start_potential, logG_bg):
    """_summary_

    Args:
        V (ndarray): _description_
        logG (ndarray): _description_
        start_potential (float): 起始电位
        logG_bg (float): 背景电导
    Returns:
        tuple(ndarray, ndarray): potential_list, conductance_list
    """    
    potential_index = np.where(~np.isclose(V, start_potential, 0.001))[0] # 可以为空
    if len(potential_index) == 0:
        return None, None
    start_index = potential_index[np.where(np.diff(potential_index) != 1)[0]+1]
    if len(start_index) == 0:
        return None, None
    start_index = np.insert(start_index, 0, potential_index[0])
    end_index = potential_index[np.where(np.diff(potential_index) != 1)]
    end_index = np.append(end_index, potential_index[-1])
    end_index = end_index + 1
    potential_list = []
    conductance_list = []
    for start, end in zip(start_index, end_index):
        trace = logG[start:end]
        if trace.min() >= logG_bg:
            potential_list.append(V[start:end])
            conductance_list.append(trace)
    # potential_list = np.array(potential_list, dtype='object')
    # conductance_list = np.array(conductance_list, dtype='object')
    return potential_list, conductance_list

    
class DataProcessor(QObject):
    runEnd = pyqtSignal()
    logger = MyLog("DataProcess", BASEDIR)

    def __init__(self, keyPara):
        super().__init__()
        self.keyPara = keyPara
        self.datasets = None
    
    def run(self):
        arg_list = []
        file_list = self.keyPara['FILE_PATHS']
        for f in file_list:
            arg_list.append((f, self.keyPara['le_start_potential'], self.keyPara['le_bg_conductance']))
        cpu_count = min(5, mp.cpu_count() - 1)
        pool = mp.Pool(cpu_count)
        self.logger.debug(f"Number of CPU core:{cpu_count},Process pool size:{cpu_count}")
        t1 = time.perf_counter()
        self.datasets = pool.starmap_async(self.dataReactor, arg_list).get()
        pool.close()
        pool.join() # 所有任务完成后关闭进程池
        t2 = time.perf_counter()
        self.logger.debug(f"Parallel time:{int(t2 - t1)}")
        self.runEnd.emit()
    def postPorcessing(self):
        try:
            p_list = []
            c_list = []
            for dataset in self.datasets:
                if dataset[0] is not None:
                        for v in dataset[0]:
                            p_list.append(v)
                        for v in dataset[1]:
                            c_list.append(v)
            if len(p_list) == 0:
                return False
            self.datasets = {}
            self.datasets['potential'] = np.array(p_list, dtype='object')
            self.datasets['conductance'] = np.array(c_list, dtype='object')
        except Exception as e:
            errMsg = f"DATA PROCESSOR FILE READ ERROR:{e}"
            self.logger.error(errMsg)
            return False
        return True
        
    @classmethod
    def dataReactor(cls, file_path, start_potential, logG_bg):
        cls.logger.debug(
            f"Computing process PID: {os.getpid()},Calculates the start time of the process: {time.perf_counter()}")
        try:
            data_v, data_c = loadTDMSFile(file_path)
        except Exception as e:
            errMsg = f"DATA PROCESSOR FILE READ ERROR:{e}"
            cls.logger.error(errMsg)
            return None, None
        else:
            try:
                data_v, data_c = cut(data_v, data_c, start_potential, logG_bg)
            except Exception as e:
                errMsg = f"DATA CUT ERROR:{e}"
                cls.logger.error(errMsg)
                return None, None
            else:
                return data_v, data_c
