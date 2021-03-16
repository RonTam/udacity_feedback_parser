import re
import json
import time
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date
from collections import defaultdict
import plotly.graph_objects as go
import plotly.express as px
import plotly
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

def get_feedback_scores():
	
    user = input('Please Enter Your Username For Your Udacity Account: \n')
    pw = input('Please Enter Your Password For Your Udacity Account: \n') 
    driver = webdriver.Firefox()
    driver.get("https://auth.udacity.com/sign-in")
    time.sleep(5)

    username = driver.find_element_by_xpath('//*[@id="email"]')
    username.send_keys(user)
    password = driver.find_element_by_xpath('//*[@id="revealable-password"]')
    password.send_keys(pw)
    driver.find_element_by_xpath('//*[@id="root"]/div/div[2]/div/div/div/div/div[2]/div[3]/div[3]/div/form/fieldset/button').click()
    time.sleep(5)
    driver.get('https://review-api.udacity.com/api/v1/me/')
    bio = driver.page_source
    print('Retriving Bio')
    soup = BeautifulSoup(bio, features="lxml")
    bio_data = soup.find_all('div', {"id": "json"})[0].text
    bio_json = json.loads(bio_data)
    try:
    	bio_name = bio_json['name']
    except:
    	bio_name = 'Anonymous'
    try:
    	bio_level = bio_json['mentor_level']
    except:
    	bio_level = "Unknown"
    
    time.sleep(5)
    driver.get('view-source:https://review-api.udacity.com/api/v1/me/student_feedbacks')
    time.sleep(5)
    content = driver.page_source
    content = driver.find_element_by_tag_name('pre').text
    data = json.loads(content)
    flatten = pd.json_normalize(data)
    temp = json.loads(content)
    COL = ['id', 'rating_cat', 'rating', 'comment']
    rows = []
    for data in temp:
        data_id = data['id']
        criteria = data['responses']['feedback']
        for d in criteria:
            rows.append([data_id, *list(d.values())[:-1]])
    df = pd.DataFrame(rows, columns = COL).drop_duplicates()
    df = df.pivot(index='id', columns = 'rating_cat', values ='rating')
    df_full = pd.merge(flatten, df, on='id')
    df_full[['review_clarity', 'review_detail', 'review_personal', 'review_unbiased', 'review_use']] = df_full[['review_clarity', 'review_detail', 'review_personal', 'review_unbiased', 'review_use']].apply(pd.to_numeric)
    df_full['average_score'] = df_full[['review_clarity', 'review_detail', 'review_personal', 'review_unbiased', 'review_use']].mean(axis=1)
    df_full['name'] = bio_name
    df_full['mentor_level'] = bio_level

    passfail = defaultdict(int)
    while True:
    	sub_count = input('How Many Submissions Would You Like To Review? Enter Your Value As An Integer or Type All To Scrape All Submissions. \n').lower()
    	if sub_count == 'all':
    		size = len(df_full)
    		break
    	elif sub_count.isnumeric():
    		size = min(len(df_full), int(sub_count))
    		break
    	else:
    		print('Invalid Entry.')

    for i in range(size):
        submission_id = df_full.iloc[i]['submission_id']
        url = 'https://review.udacity.com/#!/reviews/' + str(submission_id)
        print('Working On Submission ' + str(i+1) + ' of ' + str(size) + '. Submission Id: ' +  str(submission_id))
        driver.get(url)
        time.sleep(15)
        review = driver.page_source
        soup = BeautifulSoup(review, features="lxml")
        labels = soup.find_all("h2", class_="result-label")
    
        for i in range(len(labels)):
            if "Requires Changes" in labels[i].text:
                num_spec = re.findall(r'\d+', labels[i].text)
                passfail[str(submission_id)] = num_spec[0]
                break
            elif "Meets Specifications" in labels[i].text:
                passfail[str(submission_id)] = '0'
                break 
    pf = pd.DataFrame(passfail.items())
    pf.columns = ('submission_id','specify_change_count')
    pf[['submission_id']] = pf[['submission_id']].apply(pd.to_numeric)
    df_new = pd.merge(pf, df_full, on='submission_id')

    df_new = df_new[['submission_id', 
        'created_at',
        'project.id',
        'project.name',
        'specify_change_count',
        'review_clarity',
        'review_detail',
        'review_personal',
        'review_unbiased',
        'review_use',
        'average_score']]

    out = input('Would You Like To Save Your Output In A .csv? Type "Yes" or "No" \n').lower()    	
    if out == 'yes':
        df_new.to_csv('submissions_' + date.today().strftime("%d-%m-%Y") + '.csv')

    return df_new

def recent_ratings(ratings):
    substr = '<ul>'
    for i in ratings:
        substr +='<li><a href = "https://review.udacity.com/#!/reviews/' + str(i) + '">' + str(i) + '</a></li>'
    substr += '</ul>'
    return substr

def plot_offline(fig):
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    return plotly.offline.plot(fig,
                config={"displayModeBar": False},
                show_link=False, 
                include_plotlyjs=False, 
                output_type='div')

def build_report(df):

    size = len(df)
    low_rated = df['submission_id'][df['average_score'] < 2.].head(5)
    high_rated = df['submission_id'][df['average_score'] == 5.].head(5)
    df[['specify_change_count']] = df[['specify_change_count']].apply(pd.to_numeric)
    df['passed'] = np.where(df['specify_change_count'] == 0, True, False)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df = df.sort_values(by='created_at', ascending=True)
    df['rolling'] = df.groupby('passed')['average_score'].rolling(20).mean().reset_index(0, drop=True)

    ## Pass Fail Data
    scores_by_passfail = df[['passed','average_score']].groupby('passed').agg(['count', 'mean']).reset_index()
    try:
        met = scores_by_passfail[scores_by_passfail['passed'] == True]['average_score']['count'].fillna(0).values[0]
        met_score = scores_by_passfail[scores_by_passfail['passed'] == True]['average_score']['mean'].fillna(0).values[0]
    except:
        met = 0
        met_score = 0
    try: 
        not_met = scores_by_passfail[scores_by_passfail['passed'] == False]['average_score']['count'].fillna(0).values[0]
        not_met_score = scores_by_passfail[scores_by_passfail['passed'] == False]['average_score']['mean'].fillna(0).values[0]
    except:
        not_met = 0
        net_met_score = 0

    labels = ['Passed','Failed']
    values = [met, not_met]

    scores_by_changecnt = df[['specify_change_count','average_score']].groupby('specify_change_count').agg(['count', 'mean']).reset_index()
    scores_by_project = df[['project.name','average_score']].groupby('project.name').agg(['count', 'mean']).reset_index()

	# Make Donut
    fig = go.Figure(data=[go.Pie(labels=labels, 
	                             values=values,
                                 textfont_size=20,
                                 marker=dict(colors=['#02B3E4','#23527C']), 
	                             hole=.3)])
    donut = plot_offline(fig)

    # Make Bubble
    bsize = scores_by_changecnt['average_score']['count'].astype(float)
    fig = go.Figure(data=[go.Scatter(
                        x=scores_by_changecnt['specify_change_count'], 
                        y=scores_by_changecnt['average_score']['mean'],
                        mode='markers',
                        marker = dict(
                            color = '#23527C',
                        	size = bsize,
                        	sizeref = 2.*max(bsize)/(15.**2),
                        	sizemin=4
                        ))])
    fig.update_layout(
        xaxis_title="Count of Specified Changes (0 = Meets Specification)",
        yaxis_title="Average Score",
        font=dict(size=14)
        )
    bubble = plot_offline(fig)

    # Make Table
    fig = go.Figure(data=[go.Table(
        #header=dict(values=list(scores_by_project.columns),font=dict(size=20),height=40),
        header=dict(values=['Project Name', 'Project Count','Average Score'],font=dict(size=24),height=42),  
        cells=dict(values=[scores_by_project['project.name'],
                      scores_by_project['average_score']['count'],
                      round(scores_by_project['average_score']['mean'],2)],
                      font=dict(size=18),height=40),
        )])
    table = plot_offline(fig)

    # Make Line
    fig = px.line(df, x="created_at", y="rolling", color='passed', color_discrete_sequence=['#02B3E4','#23527C'])
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Average Score",
        font=dict(size=14)
        )
    line = plot_offline(fig)


    html_string = '''
	<html>
	    <head>
	      <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
	      <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css" integrity="sha384-9aIt2nRpC12Uk9gS9baDl411NQApFmC26EwAOH8WgZl5MYYxFfc+NcPb1dKGj7Sk" crossorigin="anonymous">
	      <link rel="preconnect" href="https://fonts.gstatic.com">
	    <link href="https://fonts.googleapis.com/css?family=Open+Sans:400,300,600" rel="stylesheet" type="text/css">    </head>
	    <body>
	        <div class="row">
	            <div class="container">
	                <img src ="https://s3-us-west-1.amazonaws.com/udacity-content/rebrand/svg/logo.min.svg" width="250" style="margin:1cm 1cm 2cm 1cm;>
	            </div>
	        </div>
	        <hr>
	        <div class="row">
	            <div class="container">
	                <h1 style = "font-family:Open Sans;font-weight: 100">
	                 Udacity Student Feedback For Ron Tam
	                </h1>
	                <hr>
	                <h6> Report Date: ''' + str(date.today().strftime("%m-%d-%Y")) + '''</h6>
	                <h2 style = "font-family:Open Sans;font-weight: 100">
	                Current Mentor Level: 3</h2>
	                <h2 style = "font-family:Open Sans;font-weight: 100">
                	Average Rating: ''' + str(round(df['average_score'].mean(),2)) + '''</h2>                
	                <br><br><hr>
	            </div>
	        </div>
	        <hr>	        
	        <div class="container">
	      		<div class="row mb-2">
	        		<div class="col-md-6">
	        		''' + donut + '''
	        		</div>
	        		<div class="col-md-6">
	        			<div class="card flex-md-row mb-4 box-shadow h-100 terms-card">
	            			<div class="card-body d-flex flex-column align-items-start">
	              				<strong class="d-inline-block mb-2">General Stats</strong>
	              				<h4 class="mb-0">
	                			Student Reviews Breakdown<br><br>
	              				</h4>
	              				<ul>
	              					<li><h5>Number of Reviews: ''' +str(size) + '''</h5></li>
	              					<li><h5>Percent Passed: ''' +str(round((met/size) * 100.,2)) + '''%</h5></li>
	              					<li><h5>Percent Failed: ''' +str(round((not_met/size) * 100.,2)) + '''%</h5></li>
	              					<li><h5>Average Score Passed: ''' +str(round(met_score,2)) + '''</h5></li>
	              					<li><h5>Average Score Failed: ''' +str(round(not_met_score,2)) + '''</h5></li>
	              				</ul>
	              				<br><br>
                  				<a href="https://mentor-dashboard.udacity.com/queue/overview" target=_blank><h5>Mentor Dashboard</h5></a>
	            			</div>
	          			</div>
	        		</div>
	      		</div>
	      		<hr>
	      		<div class="row mb-2">
	      		<h3 style = "font-family:Open Sans;font-weight: 100"> Average Scores By The Number of Specified Changes (Circle Radius = # of Reviews) </h3>
	        		<div class="col-md-12">
	        		''' + bubble + ''' </div>
	      		</div> <hr>
	      		<div class="row mb-2">
	      		   <h3 style = "font-family:Open Sans;font-weight: 100"> Average Scores By Projects </h3>
	        		<div class="col-md-12">
	        		''' + table + ''' </div>
	      		</div> <hr>
                <div class="row mb-2">
                   <h3 style = "font-family:Open Sans;font-weight: 100"> Moving Average Scores (Rolling 20 Projects) By Pass/Fail </h3>
                    <div class="col-md-12">
                    ''' + line + ''' </div>
                </div><hr>
            <div class="container">
                <div class="row mb-2">
                    
                    <div class="col-md-6">
                        <h3 style = "font-family:Open Sans;font-weight: 100"> Most Recent Low Rated Reviews </h3>
                    ''' + recent_ratings(low_rated) + '''
                    </div>

                    <div class="col-md-6">
                        <h3 style = "font-family:Open Sans;font-weight: 100"> Most Recent High Rated Reviews </h3>
                    ''' + recent_ratings(high_rated) + '''
                    </div>
                </div>

	  	    </div><hr><br>
	  	</div> 
    </body>
	</html>'''

    with open("student_feedback_report.html", 'w') as f:
        f.write(html_string)
    return

def main():
	data = input('Would You Like To Pull Your Scores From Udacity? Type "Yes" or "No" \n').lower()
	if data == 'yes':
		df = get_feedback_scores()
	else:
		fn = input('Please Enter The Name of The File You Would Like To Analyze, Adding The Path If Needed [ie: "../Projects/submissions_12-03-2021.csv" \n')
		df = pd.read_csv(fn)
	build_report(df)

if __name__ == "__main__":
    main()
