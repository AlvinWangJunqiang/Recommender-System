# -*- coding: utf-8 -*-
import random
import numpy as np
from numpy import linalg as LA
from numpy import *
import matplotlib.pyplot as plt


class PMF1(object):
    def __init__(self, num_feat=10, epsilon=1, _lambda=0.01, momentum=0.8, maxepoch=200, num_batches=10,
                 batch_size=1000):
        self.num_feat = num_feat  # Number of latent features,
        self.epsilon = epsilon  # learning rate,
        self._lambda = _lambda  # L2 regularization,
        self.momentum = momentum  # momentum of the gradient,
        self.maxepoch = maxepoch  # Number of epoch before stop,
        self.num_batches = num_batches  # Number of batches in each epoch (for SGD optimization),
        self.batch_size = batch_size  # Number of training samples used in each batches (for SGD optimization)

        self.w_C = None  # Movie feature vectors
        self.w_I = None  # User feature vecators

        self.err_train = []
        self.err_val = []
        self.data = None
        self.train_data = None
        self.test_data = None
        self.train_rmse = []
        self.test_rmse = []

    def load_rating_data(self, file_path='data/ml-100k/u.data'):
        """
        load movie lens 100k ratings from original rating file.
        need to download and put rating data in /data folder first.
        Source: http://www.grouplens.org/
        """
        prefer = []
        for line in open(file_path, 'r'):  # 打开指定文件
            (userid, movieid, rating, ts) = line.split('\t')  # 数据集中每行有4项
            uid = int(userid)
            mid = int(movieid)
            rat = float(rating)
            prefer.append([uid, mid, rat])
        self.data = array(prefer)
        return self.data

    def spilt_rating_dat(self, data, size=0.2):
        train_data = []
        test_data = []
        for line in data:
            rand = random.random()
            if rand < size:
                test_data.append(line)
            else:
                train_data.append(line)
        self.train_data = array(train_data)
        self.test_data = array(test_data)
        return self.train_data, self.test_data

        # ***Fit the model with train_tuple and evaluate RMSE on both train and validation data.  ***********#
        # ***************** train_vec=TrainData, val_vec=TestData*************#

    def fit(self, train_vec, val_vec):
        # mean subtraction
        self.mean_inv = np.mean(train_vec[:, 2])  # 评分平均值

        pairs_tr = train_vec.shape[0]  # traindata 中条目数
        pairs_va = val_vec.shape[0]  # testdata中条目数

        # 1-p-i, 2-m-c

        num_inv = int(max(np.amax(train_vec[:, 0]), np.amax(val_vec[:, 0]))) + 1  # 第0列，user总数
        num_com = int(max(np.amax(train_vec[:, 1]), np.amax(val_vec[:, 1]))) + 1  # 第1列，movie总数

        incremental = False
        if ((not incremental) or (self.w_C is None)):
            # initialize
            self.epoch = 0
            self.w_C = 0.1 * np.random.randn(num_com, self.num_feat)  # numpy.random.randn 正态分布
            self.w_I = 0.1 * np.random.randn(num_inv, self.num_feat)

            self.w_C_inc = np.zeros((num_com, self.num_feat))  # 创建0矩阵
            self.w_I_inc = np.zeros((num_inv, self.num_feat))

        while self.epoch < self.maxepoch:
            self.epoch += 1

            # Shuffle training truples
            shuffled_order = np.arange(train_vec.shape[0])  # 创建等差array
            np.random.shuffle(shuffled_order)  # 用于将一个列表中的元素打乱

            # Batch update
            for batch in range(self.num_batches):
                # print "epoch %d batch %d" % (self.epoch, batch+1)

                batch_idx = np.mod(np.arange(self.batch_size * batch, self.batch_size * (batch + 1)),
                                   shuffled_order.shape[0])

                batch_invID = np.array(train_vec[shuffled_order[batch_idx], 0], dtype='int32')
                batch_comID = np.array(train_vec[shuffled_order[batch_idx], 1], dtype='int32')

                # Compute Objective Function
                pred_out = np.sum(np.multiply(self.w_I[batch_invID, :],
                                              self.w_C[batch_comID, :]),
                                  axis=1)  # mean_inv subtracted

                rawErr = pred_out - train_vec[shuffled_order[batch_idx], 2] + self.mean_inv

                # Compute gradients
                Ix_C = 2 * np.multiply(rawErr[:, np.newaxis], self.w_I[batch_invID, :]) + self._lambda * self.w_C[batch_comID, :]
                Ix_I = 2 * np.multiply(rawErr[:, np.newaxis], self.w_C[batch_comID, :]) + self._lambda * self.w_I[batch_invID, :]

                dw_C = np.zeros((num_com, self.num_feat))
                dw_I = np.zeros((num_inv, self.num_feat))

                # loop to aggreate the gradients of the same element
                for i in range(self.batch_size):
                    dw_C[batch_comID[i], :] += Ix_C[i, :]
                    dw_I[batch_invID[i], :] += Ix_I[i, :]

                # Update with momentum
                self.w_C_inc = self.momentum * self.w_C_inc + self.epsilon * dw_C / self.batch_size
                self.w_I_inc = self.momentum * self.w_I_inc + self.epsilon * dw_I / self.batch_size

                self.w_C = self.w_C - self.w_C_inc
                self.w_I = self.w_I - self.w_I_inc

                # Compute Objective Function after
                if batch == self.num_batches - 1:
                    pred_out = np.sum(np.multiply(self.w_I[np.array(train_vec[:, 0], dtype='int32'), :],
                                                  self.w_C[np.array(train_vec[:, 1], dtype='int32'), :]),
                                      axis=1)  # mean_inv subtracted
                    rawErr = pred_out - train_vec[:, 2] + self.mean_inv
                    obj = LA.norm(rawErr) ** 2 \
                          + 0.5 * self._lambda * (LA.norm(self.w_I) ** 2 + LA.norm(self.w_C) ** 2)

                    self.err_train.append(np.sqrt(obj / pairs_tr))

                # Compute validation error
                if batch == self.num_batches - 1:
                    pred_out = np.sum(np.multiply(self.w_I[np.array(val_vec[:, 0], dtype='int32'), :],
                                                  self.w_C[np.array(val_vec[:, 1], dtype='int32'), :]),
                                      axis=1)  # mean_inv subtracted
                    rawErr = pred_out - val_vec[:, 2] + self.mean_inv
                    self.err_val.append(LA.norm(rawErr) / np.sqrt(pairs_va))

                    # Print info
                if batch == self.num_batches - 1:
                    print('Training RMSE: %f, Test RMSE %f' % (self.err_train[-1], self.err_val[-1]))
                    self.train_rmse.append(self.err_train[-1])
                    self.test_rmse.append(self.err_val[-1])
                    # ****************Predict rating of all movies for the given user. ***************#

class PMF2(object):
    def __init__(self, num_feat=10, epsilon=1, _lambda=0.001, momentum=0.8, maxepoch=200, num_batches=10, batch_size=1000):
        self.num_feat = num_feat  # Number of latent features,
        self.epsilon = epsilon  # learning rate,
        self._lambda = _lambda  # L2 regularization,
        self.momentum = momentum  # momentum of the gradient,
        self.maxepoch = maxepoch  # Number of epoch before stop,
        self.num_batches = num_batches  # Number of batches in each epoch (for SGD optimization),
        self.batch_size = batch_size  # Number of training samples used in each batches (for SGD optimization)

        self.w_C = None  # Movie feature vectors
        self.w_I = None  # User feature vecators

        self.err_train = []
        self.err_val = []
        self.data = None
        self.train_data = None
        self.test_data = None
        self.train_rmse = []
        self.test_rmse = []

    def fit(self, train_vec, val_vec):
        # mean subtraction
        self.mean_inv = np.mean(train_vec[:, 2])  # 评分平均值

        pairs_tr = train_vec.shape[0]  # traindata 中条目数
        pairs_va = val_vec.shape[0]  # testdata中条目数

        # 1-p-i, 2-m-c

        num_inv = int(max(np.amax(train_vec[:, 0]), np.amax(val_vec[:, 0]))) + 1  # 第0列，user总数
        num_com = int(max(np.amax(train_vec[:, 1]), np.amax(val_vec[:, 1]))) + 1  # 第1列，movie总数

        incremental = False
        if ((not incremental) or (self.w_C is None)):
            # initialize
            self.epoch = 0
            self.w_C = 0.1 * np.random.randn(num_com, self.num_feat)  # numpy.random.randn 正态分布
            self.w_I = 0.1 * np.random.randn(num_inv, self.num_feat)

            self.w_C_inc = np.zeros((num_com, self.num_feat))  # 创建0矩阵
            self.w_I_inc = np.zeros((num_inv, self.num_feat))

        while self.epoch < self.maxepoch:
            self.epoch += 1

            # Shuffle training truples
            shuffled_order = np.arange(train_vec.shape[0])  # 创建等差array
            np.random.shuffle(shuffled_order)  # 用于将一个列表中的元素打乱

            # Batch update
            for batch in range(self.num_batches):
                # print "epoch %d batch %d" % (self.epoch, batch+1)

                batch_idx = np.mod(np.arange(self.batch_size * batch, self.batch_size * (batch + 1)),
                                   shuffled_order.shape[0])

                batch_invID = np.array(train_vec[shuffled_order[batch_idx], 0], dtype='int32')
                batch_comID = np.array(train_vec[shuffled_order[batch_idx], 1], dtype='int32')

                # Compute Objective Function
                pred_out = np.sum(np.multiply(self.w_I[batch_invID, :],
                                              self.w_C[batch_comID, :]),
                                  axis=1)  # mean_inv subtracted

                rawErr = pred_out - train_vec[shuffled_order[batch_idx], 2] + self.mean_inv

                # Compute gradients
                Ix_C = 2 * np.multiply(rawErr[:, np.newaxis], self.w_I[batch_invID, :]) + self._lambda * self.w_C[batch_comID, :]
                Ix_I = 2 * np.multiply(rawErr[:, np.newaxis], self.w_C[batch_comID, :]) + self._lambda * self.w_I[batch_invID, :]

                dw_C = np.zeros((num_com, self.num_feat))
                dw_I = np.zeros((num_inv, self.num_feat))

                # loop to aggreate the gradients of the same element
                for i in range(self.batch_size):
                    dw_C[batch_comID[i], :] += Ix_C[i, :]
                    dw_I[batch_invID[i], :] += Ix_I[i, :]

                # Update with momentum
                self.w_C_inc = self.momentum * self.w_C_inc + self.epsilon * dw_C / self.batch_size
                self.w_I_inc = self.momentum * self.w_I_inc + self.epsilon * dw_I / self.batch_size

                self.w_C = self.w_C - self.w_C_inc
                self.w_I = self.w_I - self.w_I_inc

                # Compute Objective Function after
                if batch == self.num_batches - 1:
                    pred_out = np.sum(np.multiply(self.w_I[np.array(train_vec[:, 0], dtype='int32'), :],
                                                  self.w_C[np.array(train_vec[:, 1], dtype='int32'), :]),
                                      axis=1)  # mean_inv subtracted
                    rawErr = pred_out - train_vec[:, 2] + self.mean_inv
                    obj = LA.norm(rawErr) ** 2 \
                          + 0.5 * self._lambda * (LA.norm(self.w_I) ** 2 + LA.norm(self.w_C) ** 2)

                    self.err_train.append(np.sqrt(obj / pairs_tr))

                # Compute validation error
                if batch == self.num_batches - 1:
                    pred_out = np.sum(np.multiply(self.w_I[np.array(val_vec[:, 0], dtype='int32'), :],
                                                  self.w_C[np.array(val_vec[:, 1], dtype='int32'), :]),
                                      axis=1)  # mean_inv subtracted
                    rawErr = pred_out - val_vec[:, 2] + self.mean_inv
                    self.err_val.append(LA.norm(rawErr) / np.sqrt(pairs_va))

                    # Print info
                if batch == self.num_batches - 1:
                    print('Training RMSE: %f, Test RMSE %f' % (self.err_train[-1], self.err_val[-1]))
                    self.train_rmse.append(self.err_train[-1])
                    self.test_rmse.append(self.err_val[-1])
                    # ****************Predict rating of all movies for the given user. ***************#

if __name__ == "__main__":
    file_path = "data/ml-100k/u.data"
    pmf1 = PMF1()
    ratingdata = pmf1.load_rating_data(file_path)
    print(len(np.unique(ratingdata[:, 0])), len(np.unique(ratingdata[:, 1])), pmf1.num_feat)
    train, test = pmf1.spilt_rating_dat(ratingdata)
    pmf1.fit(train, test)

    pmf2 = PMF2()
    pmf2.fit(train, test)
    # Check performance by plotting train and test errors
    plt.plot(range(pmf1.maxepoch), pmf1.train_rmse, marker='o', label='1Training Data');
    plt.plot(range(pmf1.maxepoch), pmf1.test_rmse, marker='v', label='1Test Data');
    plt.plot(range(pmf1.maxepoch), pmf2.train_rmse, marker='o', label='2Training Data');
    plt.plot(range(pmf1.maxepoch), pmf2.test_rmse, marker='v', label='2Test Data');
    plt.title('The MovieLens Dataset Learning Curve')
    plt.xlabel('Number of Epochs');
    plt.ylabel('RMSE');
    plt.legend()
    plt.grid()
    plt.show()