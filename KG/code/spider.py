# encoding: utf-8
'''
Created on Dec 8, 2019

@author: Yongrui Huang
'''

import requests
from bs4 import BeautifulSoup
import re
import json
from collections import deque
import logging
import time
import random

def set_logging():
    """
    """
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.DEBUG,  filename='douban_spider.log', format=LOG_FORMAT)


set_logging()

def save_file(html, file_name):
    """
    """
    with open(file_name, 'w', encoding="utf-8") as f:
            f.write(html)
    
class DoubanSpider(object):
    '''
    classdocs
    '''
    #配置参数
    MOVIE_INFO_SAVE_PATH = '../data/movie_info.json'
    COMMENT_INFO_SAVE_PATH = '../data/comment.json'
    USER_INFO_SAVE_PATH = '../data/user_info.json'
    
    CONF_COOKIES_PATH = '../conf/cookies'
    CONF_WAITING_URL_PATH = '../conf/movie_urls_que'
    CONF_CRAWLED_URL_PATH = '../conf/crawled_url_set'
    CONF_COMMENT_ID_PATH = '../conf/comment_id'
    CONF_USER_URL_PATH = '../conf/user_url'
    
    WRITE_TIME = 1800
    MAX_SLEEP_TIME = 10
    
    #爬取参数
    
    session = requests.Session()
    crawled_url_set = set()
    movie_urls_que = deque([])
    movie_in_que = set()
    use_comment_page = 20
    
    user_urls_set = set()
    comments = []
    movies = []
    comment_id = 1
    
    
    def __init__(self):
        '''
        Constructor
        '''
        self.read_var_from_file()
    
    
    def reset(self):
        with open(self.CONF_COMMENT_ID_PATH, 'w') as f:
            f.write('1')
        with open(self.CONF_CRAWLED_URL_PATH, 'w') as f:
            f.write('')
        with open(self.CONF_USER_URL_PATH, 'w') as f:
            f.write('')
        with open(self.CONF_WAITING_URL_PATH, 'w') as f:
            f.write('https://movie.douban.com/subject/6560058/')
        with open(self.MOVIE_INFO_SAVE_PATH, 'w') as f:
            f.write('')
        with open(self.COMMENT_INFO_SAVE_PATH, 'w') as f:
            f.write('')
            
            
    def write_file(self):
        """
        """
        logging.info('writing file ...')
        self.write_var2file()
        self.save_comments()
        self.save_movie_info()

 
    def read_var_from_file(self):
        """
        """
        with open(self.CONF_CRAWLED_URL_PATH, 'r') as f:
            for line in f:
                url = line.strip()
                if len(url) > 5:
                    self.crawled_url_set.add(url)
    
        with open(self.CONF_WAITING_URL_PATH, 'r') as f:
            for line in f:
                url = line.strip()
                if len(url) > 5:
                    self.movie_urls_que.append(line.strip())
                    self.movie_in_que.add(line.strip())

        with open(self.CONF_COMMENT_ID_PATH, 'r') as f:
            self.comment_id = int(f.read().strip())
            
        with open(self.CONF_USER_URL_PATH, 'r') as f:
            for line in f:
                url = line.strip()
                if len(url) > 5:
                    self.user_urls_set.add(url)


    def write_var2file(self):
        """
        """
        with open(self.CONF_CRAWLED_URL_PATH, 'w') as f:
            for url in self.crawled_url_set:
                f.write(url)
                f.write('\n')
    
    
        with open(self.CONF_WAITING_URL_PATH, 'w') as f:
            for url in self.movie_urls_que:
                f.write(url)
                f.write('\n')
                
                
        with open(self.CONF_COMMENT_ID_PATH, 'w') as f:
            f.write(str(self.comment_id))
    
    
        with open(self.CONF_USER_URL_PATH, 'w') as f:
            for url in self.user_urls_set:
                f.write(url)
                f.write('\n')
                
                
    def save_comments(self):
        """
        """
        with open(self.COMMENT_INFO_SAVE_PATH, 'a', encoding='utf-8') as f:
            for comment in self.comments:
                f.write(json.dumps(comment, ensure_ascii=False))
                f.write('\n')
        self.comments = []

    def save_user_info(self, user_info):
        """
        """
        with open(self.USER_INFO_SAVE_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(user_info, ensure_ascii=False))
            f.write('\n')

    
    def save_movie_info(self):
        """
        """
        with open(self.MOVIE_INFO_SAVE_PATH, 'a', encoding='utf-8') as f:
            for movie in self.movies:
                f.write(json.dumps(movie, ensure_ascii=False))
                f.write('\n')
        self.movies = []
      
    def login(self):
        """
                                登录豆瓣
        :return:
        """
        with open(self.CONF_COOKIES_PATH, 'r') as f:
            cookies = f.read()
        self.session.cookies.set("authentication", cookies)
        
        headers = {'user-agent': 'Mozilla/5.0'}
        url = "https://www.douban.com/accounts/"
        login_code = self.session.get(url, headers=headers,
                                 allow_redirects=False).status_code
        if login_code == 200:
            logging.info('cookies 登录成功')
            return True
        else:
            logging.info('cookies 登录失败，请更新cookies')
            return False


    def get_user_urls_from_url(self, url):
        """
        """
        html = self.url2html(url)
        soup = BeautifulSoup(html, "html.parser")
        users = soup.findAll('dl', 'obu')
        user_urls = []
        for user in users:
            user_urls.append(user.find('a', href = re.compile(r"https://www.douban.com/people/.*"))['href'])
            
        return user_urls


    def get_string(self, html):
        if html is None:
            return ''
        else:
            return html.string

             
    def parse_people(self, html):
        """
        """
        if(html.find('该用户已经主动注销帐号') != -1):
            return {'type':'注销用户'}
        soup = BeautifulSoup(html, "html.parser")
        data = {}
        data['niki_name'] = soup.find('div', 'info').contents[1].get_text()
        data['wish_movie_num'] = self.get_string(soup.find('a', href = re.compile(r"https://movie.douban.com/people/.*/wish")))
        data['collect_movie_num'] = self.get_string(soup.find('a', href = re.compile(r"https://movie.douban.com/people/.*/collect")))
        data['do_movie_num'] = self.get_string(soup.find('a', href = re.compile(r"'https://movie.douban.com/people/.*/do'")))
        data['location'] = self.get_string(soup.find('div', 'user-info').contents[1])
        #改进
        #data['join_time'] = soup.find('div', 'pl').contents[2][:-2].strip()
        Following_url = soup.find('a', href = re.compile(r"https://www.douban.com/people/.*/contacts"))['href']
        Followers_url = soup.find('a', href = re.compile(r"https://www.douban.com/people/.*/rev_contacts"))['href']
        data['following'] = self.get_user_urls_from_url(Following_url)
        data['followers'] = self.get_user_urls_from_url(Followers_url)
        return data


    def parse_commit_page(self, html, page_num):
        """
        """
        soup = BeautifulSoup(html, "html.parser")
        datas = []
        comment_items = soup.find_all('div', 'comment-item')
#         comment_items = soup.find_all('div', 'comment')

        rank = 1
        for comment_item in comment_items:  
            data = {}     
            
            data['user_url'] = comment_item.find('a', href = re.compile(r"https://www.douban.com/people/.*"))['href']
            data['comment_text'] = comment_item.find('span', 'short').string
            data['votes'] = comment_item.find('span', 'votes').string
            data['star'] = comment_item.find('span', 'comment-info').contents[5]['class'][0][-2]
            data['comment_time'] = comment_item.find('span', 'comment-time')['title']
            data['watch_type'] = comment_item.find('span', 'comment-info').contents[3].string
            data['rank'] = rank + page_num * 20
            data['comment_id'] = self.comment_id
            self.comment_id += 1
            rank += 1
            datas.append(data)
        if page_num == 0:
            collect_num = soup.find('ul', 'fleft CommentTabs').contents[1].get_text().strip()[3:-1]
            wish_num = soup.find('ul', 'fleft CommentTabs').contents[3].get_text().strip()[3:-1]
            return datas, collect_num, wish_num
        
        return datas
    
    
    def parse_movie_page(self, html):
        """
        """
        soup = BeautifulSoup(html, "html.parser")
        
        data = {}
        data['score'] = soup.find('strong',  class_ = "ll rating_num").get_text()
        data['title'] = soup.find('div', id = "content").find('h1').get_text()
        data['summary'] = soup.find('span', property="v:summary").get_text().strip()
        
        names_html = soup.find_all('span',  attrs={"class":"attrs"})
        def get_name_html(names_html):
            
            res = []
            for name_html in names_html:
                name = name_html.string.strip().replace('/', '')
                if(len(name) > 0):
                    res.append(name)
            return res
        
        #导演
        data['directors'] = get_name_html(names_html[0])
        #编剧
        data['writer'] = get_name_html(names_html[1])
        #演员
        data['actor'] = get_name_html(names_html[2])
        #国家
        data['country'] = soup.find('span', text='制片国家/地区:').next_sibling
        #时长
        data['minutes'] = soup.find('span', property='v:runtime').string
        
        #类型：科幻、动作等
        data['type'] = []
        movie_types = soup.find_all('span',  property="v:genre")
        for movie_type in movie_types:
            data['type'].append(movie_type.string)
        
        #上映日期
        data['releasedDate'] = []
        released_dates = soup.find_all('span',  property="v:initialReleaseDate")
        for released_date in released_dates:
            data['releasedDate'].append(released_date.string)
        
        #又名
#         data['another_name'] = soup.find('span', text='又名:').next_sibling.split(' / ')
        recommended_urls = []
        links = soup.find_all('a', href = re.compile(r"https://movie.douban.com/subject/\d+/\?from=subject-page"))
        for link in links:
            L = link['href'].split('/')
            tot = len(link['href'])
            cutted = len(L[-1])
            recommended_urls.append(link['href'][0:tot-cutted])
        
        data['recommended_urls'] = recommended_urls
        return data
    
    
    def url2html(self, url):
        """
        """
        time.sleep(random.random() * self.MAX_SLEEP_TIME)
        # 请求头
        headers = {'user-agent': 'Mozilla/5.0'}
        try:
            r = self.session.get(url, headers=headers)
            r.raise_for_status()
        except:
            logging.debug("fail to download url : %s" % url)

            return -1
        return r.text
    
    
    def crawl_comment(self, movie_url):
        """
        Args:
            movie_url: 电影地址，比如： https://movie.douban.com/subject/1905462/
        Returns:
            status:
        """
        page = 0
        start = int(page * 20)
        comment_url = '%scomments?start=%d&limit=20&sort=new_score&status=P' % (movie_url, start)
        html = self.url2html(comment_url)
        comments, collected_num, wish_num = self.parse_commit_page(html, 0)
        max_page = int(collected_num) / 20
        use_page = min(self.use_comment_page, max_page)
        for page in range(1, use_page):
            logging.info('crawl movie comment %s page %d' %(movie_url, page))
            start = int(page * 20)
            comment_url = '%scomments?start=%d&limit=20&sort=new_score&status=P' % (movie_url, start)
            html = self.url2html(comment_url)
            new_comments = self.parse_commit_page(html, page)
            comments.extend(new_comments)
 
        return comments, collected_num, wish_num
    
    
    def crawl_movie_page(self, url):
        """
        """
        html = self.url2html(url)
        movie_data = self.parse_movie_page(html)
        return movie_data
    
    
    def start_crawl(self):
        
        self.login()
        last_time = time.time()
        while(len(self.movie_urls_que) > 0):
            
            movie_url = self.movie_urls_que.popleft()
            if(movie_url in self.crawled_url_set):
                continue
            self.crawled_url_set.add(movie_url)
            try:
                movie_data = self.crawl_movie_page(movie_url)
                comment_datas, collected_num, wish_num = self.crawl_comment(movie_url)
            except:
                logging.error('crawl failed in %s' % movie_url)
                continue
            movie_data['collected_num'] = collected_num
            movie_data['wish_num'] = wish_num
            movie_data['movie_url'] = movie_url
            
            for next_url in movie_data['recommended_urls']:
                if next_url not in self.crawled_url_set and next_url not in self.movie_in_que:
                    self.movie_urls_que.append(next_url)
                    self.movie_in_que.add(next_url)

            for comment_data in comment_datas:
                comment_data['movie_url'] = movie_url
                user_url = comment_data['user_url']
                self.user_urls_set.add(user_url)
#                 user_html = self.url2html(user_url)
#                 user_data = self.parse_people(user_html)
#                 user_data['user_url'] = user_url
#                 self.save_user_info(user_data)
                
            self.movies.append(movie_data)
            self.comments.extend(comment_datas)
            now = time.time()
            if(now - last_time > self.WRITE_TIME):
                self.write_file()
                last_time = time.time()

            
def load_comments(file_path):
    comments = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            comment = json.loads(line.strip())
            print(comment)
            comments.append(comment)
    return comments

if __name__ == "__main__":
    douban_spider = DoubanSpider()
#     douban_spider.start_crawl()
    html = douban_spider.url2html('https://movie.douban.com/subject/1299995')
    data = douban_spider.parse_movie_page(html)
    print(data)