import crochet
crochet.setup()

from flask import Flask , render_template, jsonify, request, redirect, url_for
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.signalmanager import dispatcher
import time
import os

import sqlite3 as sql 

# Importing our Scraping Function from the amazon_scraping file

from crawlshop.crawlshop.spiders.amazon_scraping import ReviewspiderSpider

# Creating Flask App Variable

app = Flask(__name__)

output_data = []
crawl_runner = CrawlerRunner()

# By Deafult Flask will come into this when we run the file
@app.route('/')
def index():
	return render_template("index.html") # Returns index.html file in templates folder.


# After clicking the Submit Button FLASK will come into this
@app.route('/', methods=['POST'])
def submit():
    if request.method == 'POST':
        s = request.form['url'] # Getting the Input Amazon Product URL
        global baseURL
        baseURL = s
        
        # This will remove any existing file with the same name so that the scrapy will not append the data to any previous file.
        if os.path.exists("<path_to_outputfile.json>"): 
                os.remove("<path_to_outputfile.json>")

        return redirect(url_for('scrape')) # Passing to the Scrape function


@app.route("/scrape")
def scrape():
    global baseURL
    global output_data
    
    # Getting the unique table name from the input URL.
    table_name = baseURL.split("?")[0]
    
    # Creating a connection to database
    conn = sql.connect('database.db')

    # Creating an object of the Database to perform the operations.
    c = conn.cursor()
    
    # This will extract the count of tables with name='<table_name>'
    # It can only be zero or one.
    c.execute('''SELECT count(name) FROM sqlite_master WHERE name='%s' AND type='table' '''%table_name)

    if(c.fetchone()[0]==0):

    # Passing the URL for Scraping
        scrape_with_crochet(baseURL=baseURL) # Passing that URL to our Scraping Function
        time.sleep(10) # Pause the function while the scrapy spider is running
        # Scraped Data is appended to the output_list

        # Creating the table with name = <table_name>
        # Note: table_name will be unique for each product
        conn.execute('''CREATE TABLE '%s' (names TEXT,  reviewerLink TEXT, reviewTitles TEXT, reviewBody TEXT, verifiedPurchase TEXT, postDate TEXT, starRating TEXT, helpful TEXT, nextPage TEXT)''' %table_name)

        # Appending the data into the table from the output_list
        for x in output_data:
            c.execute('''INSERT INTO '%s' (names, reviewerLink, reviewTitles, reviewBody, verifiedPurchase, postDate, starRating, helpful, nextPage) VALUES (?,?,?,?,?,?,?,?,?)''' %table_name ,(x["names"], x["reviewerLink"], x["reviewTitles"], x["reviewBody"], x["verifiedPurchase"], x["postDate"], x["starRating"], x["helpful"], x["nextPage"]))

        conn.commit()
        conn.close()

        print("Table and Records created Successfully!")

    else: # The code will come here if it finds the URL data in the DB
        conn.row_factory = sql.Row
        cur = conn.cursor()
        
        # Selecting everything from the table inside the DB.
        cur.execute(''' SELECT * from '%s' '''%table_name)

        # Fetching the data from the cur object.
        rows = cur.fetchall()
        
        # Storing the fetched data into the global output_data list.
        output_data = [dict(i) for i in rows]

        conn.close()

        print("Data Fetched Successfully!")
    
    return jsonify(output_data) # Returns the scraped data after being running for 20 seconds.


@crochet.run_in_reactor
def scrape_with_crochet(baseURL):
    # This will connect to the dispatcher that will kind of loop the code between these two functions.
    dispatcher.connect(_crawler_result, signal=signals.item_scraped)
    
    # This will connect to the ReviewspiderSpider function in our scrapy file and after each yield will pass to the crawler_result function.
    eventual = crawl_runner.crawl(ReviewspiderSpider, category = baseURL)
    return eventual

#This will append the data to the output data list.
def _crawler_result(item, response, spider):
    output_data.append(dict(item))


if __name__== "__main__":
    app.run(debug=True)