# Author: Yue Chen

#import libraries
import os

# custom modules
import resume
import indeed_job_scraper as indeed

#dataframe
import pandas as pd
import numpy as np

import re

#nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

#vectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

#word2vec
from gensim.models import TfidfModel
from gensim.models import Word2Vec

from gensim import corpora
from gensim.matutils import softcossim 

from gensim.models.keyedvectors import WordEmbeddingSimilarityIndex
from gensim.similarities import SparseTermSimilarityMatrix,SoftCosineSimilarity


def preprocess(text):
    '''
    Remove line changes (\n), non-alphabets, and stopwords from input text
    and return a list of words in the text.
    '''
    text = text.lower().replace('\n',' ')
    text = re.sub('[^A-Za-z]',' ',text)

    stopwords_list = stopwords.words('english')

    words = word_tokenize(text)
    no_stopwords = [w for w in words if w not in stopwords_list]
    return no_stopwords

def skill_score(res_skills, skills):
    '''
    Measures the percent of skills in the resume that is required by the job
    and also the percent of skills required that appears in the resume.
    The latter measure helps to exclude jobs that do not list many skills from having a high skill score.
    '''
    skills = skills.split('|')
    common_skills = list(set(res_skills) & set(skills))
    percent_skills = len(common_skills) / len(skills) + 0.5*(len(common_skills) / len(res_skills))
    return percent_skills


def resume_match(file):
    #Extract resume
    res = resume.extract_text(file)
    obj_exp = resume.get_obj_exp(res)
    res_skills = resume.extract_skills(res)
    
    #get job
    # job_dict = indeed.get_indeed_job(job_title,location)
    
    #Use data scientist at Irvine as test
    job_df = pd.read_csv('indeed_job_data_scientist_irvine.csv')
    job_df = job_df.dropna().drop_duplicates()
    job_dict = job_df.to_dict(orient='list')

    comp_text = [obj_exp] + job_dict['description']
    corpus = [preprocess(txt) for txt in comp_text]
    dictionary = corpora.Dictionary(corpus)
    text_process = [dictionary.doc2bow(txt) for txt in corpus]

    tfidf = TfidfModel(dictionary=dictionary)
    w2v = Word2Vec(corpus, min_count=5, size=300, seed=12345)
    sim_index = WordEmbeddingSimilarityIndex(w2v.wv,threshold=0.0,exponent=2.0)
    sim_mat = SparseTermSimilarityMatrix(sim_index, dictionary,
                                     tfidf,
                                     nonzero_limit=100)
    

    job_score = {'job':[],'word2vec':[],'tfidf_vectorizer':[],'company':[],'description':[],'skills':[],'skill_score':[]}
    for i in range(0,len(job_dict['title'])):
        job_score['job'].append(job_dict['title'][i])
        
        #word2vec
        similarity = sim_mat.inner_product(text_process[0], text_process[i+1], normalized=True)
        job_score['word2vec'].append(similarity)
        
        #tfidf vectorizer
        tv = TfidfVectorizer(use_idf=True, stop_words='english')
        tv_fit = tv.fit_transform([obj_exp, job_dict['description'][i]])
        job_score['tfidf_vectorizer'].append(cosine_similarity(tv_fit)[0][1])
        
        job_score['company'].append(job_dict['company'][i])
        job_score['description'].append(job_dict['description'][i])
        job_score['skills'].append(job_dict['skill'][i])
        job_score['skill_score'].append(skill_score(res_skills, job_dict['skill'][i]))
        
    job_score_df= pd.DataFrame(job_score)
    job_score_df['score'] = (
                         (job_score_df.word2vec / job_score_df.word2vec.max())
                       + (job_score_df.tfidf_vectorizer / job_score_df.tfidf_vectorizer.max())
                       + (job_score_df.skill_score / job_score_df.skill_score.max())
                         )
    job_score_df = job_score_df.sort_values(by='score',ascending=False).reset_index(drop=True)

    return job_score_df[['job','company','description']]

