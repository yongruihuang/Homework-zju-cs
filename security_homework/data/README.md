# 安装依赖
运行环境python3.6，pytorch 1.1.0
在对应python版本下，运行文件夹内的requirements.txt

    pip install -r requirements.txt


# 运行测试集

读取base model结果,stacking model，进行预测

    source run.sh

# 从头开始训练模型,从特征构建开始

    sourcr train.sh
    
# train.sh关键代码执行逻辑

## Step 1: 数据预处理
进入src/fjw目录，执行

    jupyter nbconvert --to script *.ipynb
    
得到目录下所有notebook转换的.py文件
    
    nohup python data_preprocess.py > log.data_preprocess

执行数据预处理，包括
- 生成每个action对应的target encode
- 生成统计聚合特征
- 生成tf-idf sequence和textrank sequence
- 生成各个id分别生成对应sequence文件，同时对部分id序列进行了shuffle，增加model输入多样性。

进入GloVe-master，生成各个id序列的glove词向量

    cd GloVe-master/
    jupyter nbconvert --to script generate_glove.ipynb
    nohup python generate_glove.py > log.generate_glove


进入src/hyr目录

    nohup python main.py > log.main
    
数据预处理，包括：
- 生成各个id的序列用于后续操作
- 使用tf-idf特征做stacking生成对于每个用户样本的特征
- 生成各个id序列的word2vec词向量

合并词向量（加快访问速度，节省内存）

    cd ../fjw
    nohup python merge.py > log.merge
    cd ../hyr
    nohup python merge.py > log.merge

## Step 2: 训练模型

- 使用了ESIM,RE2,transfomer 3种基本模型，并进行以下优化
- ESIM & RE2: 将esim和re2的pair sequence输入改造成单输入，作为额外的模型和原本的模型融合
- ESIM & RE2: ESIM和RE2除了原本的输入，使用了time和click time的embedding，引入time和click time信息
- ESIM: 改造了ESIM的点积注意力部分，引入SVD形式的注意力，此外，在ESIM第二层LSTM之前使用residual机制将模型输入和之前block的输出拼接输入最后的LSTM中
- Transfomer: 使用time sequence作为transfomer position embedding的index，同时，使用click对attention部分权重进行缩放
- RE2: RE2的单输入模型将max pool和sum pool拼接作为hidden
- 学习策略: 部分model使用了label smoothing，才用AdamW为优化器，使用线性的learing rate scheduler.


    cd ../fjw
    nohup python train_ESIM_glove200.py > log.train_ESIM_glove200
    nohup python train_ESIM_glove50.py > log.train_ESIM_glove50
    '''
    
    cd ../hyr
    nohup python train_re2_50dim_20_class.py > log.train_re2_50dim_20_class
    nohup python train_re2_one_200caa_glove_lr0003_smooth_wd005.py > log.train_re2_one_200caa_glove_lr0003_smooth_wd005
    '''

Step 3: 模型融合

    cd ../hyr
    nohup python sort_out_model_ret.py > log.sort_out_model_ret #整理输出数据
    cd ../../stack
    jupyter nbconvert --to script *.ipynb
    nohup python stack.py > log.stack #融合模型
