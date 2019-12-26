# encoding: utf-8
'''
Created on Dec 17, 2019

@author: Yongrui Huang
'''

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import jieba
import pandas as pd
import numpy as np
import re

class CommentCompare(object):
    '''
    classdocs
    
   A sample:
    {
    'movie': {
              'title': '\n雷神2：黑暗世界 Thor: The Dark World\n(2013)\n',
              'summary': '纽约大战后，雷神索尔（克里斯·海姆斯沃斯 Chris Hemsworth 饰）将弟弟洛基（汤姆·希德勒斯顿 Tom Hiddleston 饰）带回仙宫囚禁起来，此外帮助九大国度平定纷争，威名扶摇直上。虽然父王奥丁（安东尼·霍普金斯 Anthony Hopkins 饰）劝其及早即位，但索尔念念不忘地球的美丽女孩简·福斯特（娜塔丽·波特曼 Natalie Portman 饰）。与此同时，简在和黛西及其助手伊安调查某个区域时意外被神秘物质入侵，却也因此重逢索尔，并随其返回仙宫。令人意想不到的是，藏在简体内的物质来自远古的黑暗精灵玛勒基斯（克里斯托弗·埃克莱斯顿 Christopher Eccleston 饰）。在“天体汇聚”的时刻再次到来之际，玛勒基斯企图摧毁九大国度，缔造一个全然黑暗的宇宙。\n                                        \n                                    \u3000\u3000藏匿简的仙宫受到重创，而索尔和洛基这对冤家兄弟也不得不联手迎战...',
              'directors': ['阿兰·泰勒'],
              'writer': ['克里斯托弗·约斯特', ...],
              'actor': ['克里斯·海姆斯沃斯',...],
              'type': ['动作', '奇幻', ...],
              'movie_url': 'https://movie.douban.com/subject/6560058/' 
              },
     'comment_a': {
            'user_url': 'https://www.douban.com/people/questwoo/',
            'comment_text': '我能体会到波特曼看到雷神和洛基生离死别时那种电灯泡的感觉',
            'comment_id': 1,
            },
     'comment_b': {
            'user_url': 'https://www.douban.com/people/yangchen1102/',
            'comment_text': '奈特莉还真够平',
            'comment_id': 250749,
            }
    }
    
    y_i : 1 indicate comment_a is better than comment_b for movies, 0 otherwise.
    '''
    
    tfidf_vec_movie = None
    svd_movie = None
    tfidf_vec_comment = None
    svd_comment = None
    movie_feature_name = None
    lgb_clf = None
    
    stop_words = set()
    cnt_movie_num = 0
    def __init__(self, params):
        '''
        Constructor
        '''
        self.load_stopwords()
        self.tfidf_vec_movie = params['tfidf_vec_movie']
        self.svd_movie = params['svd_movie']
        self.tfidf_vec_comment = params['tfidf_vec_comment']
        self.svd_comment = params['svd_comment']
        self.movie_feature_name = params['movie_feature_name']
        self.lgb_clf = params['lgb_clf']

        
    def predict(self, samples):
        
        movie_texts = []
        movies = []
        for sample in samples:
            movie = sample['movie']
            movies.append(movie)
            movie_texts.append(self.clean_text(movie['title'] + movie['summary']))
        df_movies = pd.DataFrame(np.zeros((len(samples), len(self.movie_feature_name))), columns = self.movie_feature_name)
        self.cnt_movie_num = 0
        def set_features(x):
            movie = movies[self.cnt_movie_num]
            self.cnt_movie_num += 1
            x[movie['type']] = 1
            x['len_directors'] = len(movie['directors'])
            x['len_writer'] = len(movie['writer'])    
            x['len_actor'] = len(movie['actor'])    
            x['len_title'] = len(self.clean_text(movie['title']))
            x['len_summary'] = len(self.clean_text(movie['summary']))
        _ = df_movies.apply(set_features, axis = 1)

        movie_texts_tfidf_svd = self.predict_tfidf_svd_matrix(movie_texts, self.tfidf_vec_movie, self.svd_movie)
        tf_idf_movie_columns_names = ['td_idf_movie_%d' % i for i in range(movie_texts_tfidf_svd.shape[1])]
        #1
        df_tf_idf_movie_svd = pd.DataFrame(movie_texts_tfidf_svd, columns = tf_idf_movie_columns_names)
        df_movies_with_tfidf = pd.concat([df_movies, df_tf_idf_movie_svd], axis=1)
        
        comments_text_a = []
        comments_text_b = []
        for sample in samples:
            comments_text_a.append(sample['comment_a']['comment_text'])
            comments_text_b.append(sample['comment_b']['comment_text'])
        
        #2
        comment_texts_a_tfidf_svd = self.predict_tfidf_svd_matrix(comments_text_a, self.tfidf_vec_comment, self.svd_comment)
        #3
        comment_texts_b_tfidf_svd = self.predict_tfidf_svd_matrix(comments_text_b, self.tfidf_vec_comment, self.svd_comment)
        
        hit_feature_number = 5
        #4
        X_hit_features = np.zeros((len(samples), hit_feature_number * 2))

        for i, sample in enumerate(samples):            
            X_hit_features[i][:hit_feature_number] = self.get_feature_movie_comment(sample['movie'], sample['comment_a'])
            X_hit_features[i][hit_feature_number:] = self.get_feature_movie_comment(sample['movie'], sample['comment_b'])
        
        X_all = np.concatenate((df_movies_with_tfidf.values, comment_texts_a_tfidf_svd, \
                                comment_texts_b_tfidf_svd, X_hit_features), axis = 1)
        
        return self.lgb_clf.predict(X_all), X_all
    
    
    def get_common_substrs(self, str1, str2, min_len):
        """
                        在str1中寻找出现在str2的子串
        """
        substr_list = []  # 保存两者相同的子串
        s = 0  # 记录str1起始位置
        e = 1  # 记录str1终止位置
        match_num = 0  # 匹配个数
        is_final = False  # 是否结束匹配过程：终止位置到达str1的最后一个位置
        while not is_final:
            cur_str = str1[s:e]
            if cur_str in str2:
                match_num += 1
                if e == len(str1):
                    if len(cur_str) >= min_len:
                        substr_list.append(str1[s:s + match_num])
                    is_final = True
                else:
                    e += 1
            else:
                if match_num < min_len:
                    s += 1
                    if e != len(str1):
                        e += 1
                else:
                    substr_list.append(str1[s:s + match_num])
                    s = s + match_num
                    e = s + 1
                    match_num = 0
        return substr_list
    
    
    def get_feature_movie_comment(self, movie, comment):
        """
        Args:
            movie:
            comment:
        Returns:
            vector:
                                            第一维：命中电影summary长度为2的数量累积加权
                                            第二维：命中电影summary长度大于2的数量累积加权
                                            第三维：命中导演数量
                                            第四维：命中编剧数量
                                            第五维：命中演员数量
        """
        comment_text = re.sub('，|“|”|、|；|、|。|…|\.|的|时候|个|·|）|（| ', '', comment['comment_text'])
        len_comment = len(comment_text)
        len_movie_summary = len(movie['summary'])
        vector = np.zeros((5,))
        if(len_comment == 0):
            return vector
        
        substr_list = self.get_common_substrs(comment_text, movie['summary'], 2)
        for i, sub_srt in enumerate(substr_list):
            len_sub_str = len(sub_srt)
            if(len_sub_str == 2):
                vector[0] += 2
            elif(len_sub_str > 2):
                vector[1] += len_sub_str
        for director in movie['directors']:
            substr = self.get_common_substrs(director, comment_text, 2) 
            if(len(substr) > 0):
                vector[2] += 1
        
        
        for writer in movie['writer']:
            substr = self.get_common_substrs(writer, comment_text, 2) 
            if(len(substr) > 0):
                vector[3] += 1
    
        for actor in movie['actor']:
            substr = self.get_common_substrs(actor, comment_text, 2) 
            if(len(substr) > 0):
                vector[4] += 1
        
        return vector
    
    
    def predict_tfidf_svd_matrix(self, texts, tfidf_vec, svd):
        """
        """
        corpus = []
        for text in texts:
            words = self.word_segment(str(text))
            use_words = []
            for word in words:
                if word in self.stop_words:
                    continue
                else:
                    use_words.append(word)
            corpus.append(' '.join(use_words))
            
        tfidf_matrix = tfidf_vec.transform(corpus)
        tf_idf_svd = svd.transform(tfidf_matrix)
        
        return tf_idf_svd


    def word_segment(self, sentence):
        words = jieba.cut(sentence)
        return ','.join(words).split(',')
    
    def load_stopwords(self):
        """
        """
        with open('../middle_data/stopwords.txt', 'r', encoding='UTF-8') as f:
            for line in f.readlines():
                self.stop_words.add(line.strip())
        
    def remove_stopwords(self, word_lists):
        """
        """
        res = []
        for word in word_lists:
            if word not in self.stop_words:
                res.append(word)
        return ' '.join(res)
     
    def clean_text(self, string):
        return string.replace(' ', '').replace('\n', '').replace('\u3000', '')


from joblib import load
import lightgbm as lgb
import json
import logging
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.DEBUG,  filename='douban_spider.log', format=LOG_FORMAT)

if __name__ == '__main__':
    print('This is an example of using it for comment comparing')
    
    movie_features = load('../middle_data/movie_features.sk.var')
    tfidf_vec_movie = load('../middle_data/tfidf_vec_movie.sk.model')
    svd_movie = load('../middle_data/svd_movie.sk.model')
    tfidf_vec_comment = load('../middle_data/tfidf_vec_comment.sk.model')
    svd_comment = load('../middle_data/svd_comment.sk.model')
    lgb_clf = lgb.Booster(model_file='../middle_data/lgb_clf_base.txt')
    
    logging.info('finish loading model.....')
    
    params = {
        'tfidf_vec_movie': tfidf_vec_movie,
        'svd_movie': svd_movie,
        'tfidf_vec_comment':tfidf_vec_comment,
        'svd_comment':svd_comment,
        'movie_feature_name':movie_features,  
        'lgb_clf':lgb_clf,
    }
    decoder = CommentCompare(params)
    build_sample = {
        'movie':{'actor': ['米哈乌·多科罗曼斯基', '米洛斯·科佩基', '鲁道夫·霍辛斯基', '纳达·康瓦林科夫'],
                 'type': ['喜剧', '犯罪'], 
                 'summary': '美国最伟大的侦探尼克·卡特又有了新难题！一位布拉格贵妇家发生一起离奇的失踪案，卡特火速启程，不料却发现案件比预想还要脱轨。多年前沉入沼泽的死对头为何重现江湖？种满毒草的温室内又究竟隐藏了怎样的秘密？卡特无所不用其极，搬出化学实验台，戴上拳拳防身帽，一边收拾助手的烂摊子，一边周旋于自己的老对头。捷克经典馆藏全新修复，史云梅耶亲自上阵设计动画，为影片带来夸张又癫狂的视觉效果。事不宜迟……先坐下来喝杯当地风味纯正的皮尔森酒，咬上几口香肠，再看卡特和他的助手如何擒拿罪犯。', 
                 'title': '\n阿黛尔还没吃晚餐 Adéla jeste nevecerela\n(1978)\n', 
                 'directors': ['奥德里奇·利普斯基'], 
                 'writer': ['伊里·布尔德奇卡']},
        'comment_a':{
             'comment_text':"这也太搞笑了吧，尼克随随便便就破案了",
        },
        'comment_b':{
            'comment_text':'定格+真人，史上装备最全的侦探智斗恶魔科学家，笑料足，脑洞大，充满东欧式讽谑喜剧味；各种新奇设备的加持，为简单欢乐的破案提升“技术”参数。身披黑袍屋顶行走，如佐罗附身，身形殊异的双侦探模式+不死的“莫里亚蒂”第二可持续拍成系列。另外，可迅速美颜+减肥的神奇药丸请给我来一百颗。'
        }
    }
    y, X = decoder.predict([build_sample])
    
    print('an input sample:')
    print(json.dumps(build_sample, sort_keys=True, indent=4, separators=(',', ':'), ensure_ascii = False))
    print('feature:')
    print(X[0])
    print('result:')
    print(y[0])
    