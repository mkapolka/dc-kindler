#!/usr/bin/python

import argparse;
from urllib import urlopen;
import urllib;
import lxml.html
import os;
import Queue;
import threading;
import socket;

#Constants
ARCHIVE_URL = 'http://www.qwantz.com/archive.php';
COMIC_URL = 'http://www.qwantz.com/index.php';
TIMEOUT = 30;

#Helper Methods
def get_comic(object):
   page = urlopen(object.getPageUrl());
   dom = lxml.html.parse(page);

   #find the comic
   for img in dom.iter("img"):
      if (img.attrib.get('class', False) and img.attrib['class'] == 'comic'):
         object.setComicUrl(img.attrib['src']);
         object.setAltText(img.attrib['title']);
         object.setFilename(str(object.getIndex()) + ".png");

         #print("Downloading: " + object.getComicUrl());
         imgopener.retrieve(object.getComicUrl(), comic_dir + "/" + str(object.getIndex()) + ".png");

def get_comic_index(page_url):
   param_index = page_url.find("comic=");
   return page_url[param_index + len("comic="):];

#Classes
class ComicQueueItem:
   def __init__(self):
      self.comic_url = "";
      self.page_url = "";
      self.filename = "";
      self.alt_text = "";
      self.index = 0;
      self.failed = False;

   def getComicUrl(self):
      return self.comic_url;

   def setComicUrl(self, comic_url):
      self.comic_url = comic_url;

   def getPageUrl(self):
      return self.page_url;

   def setPageUrl(self, page_url):
      self.page_url = page_url;

   def getFilename(self):
      return self.filename;

   def setFilename(self, filename):
      self.filename = filename;

   def getAltText(self):
      return self.alt_text;

   def setAltText(self, alt_text):
      self.alt_text = alt_text;

   def getIndex(self):
      return self.index;

   def setIndex(self, value):
      self.index = value;

   def setFailed(self, value):
      self.failed = value;

   def getFailed(self):
      return self.failed;

class DownloadComicThread(threading.Thread):
   def __init__(self, queue):
      threading.Thread.__init__(self);
      self.queue = queue;

   def run(self):
      while not queue.empty():
         try:
            item = queue.get();
            print(str(self.ident) + " Opening " + item.getPageUrl());
            get_comic(item);
            queue.task_done();
         except:
            print("Exception in Thread " + str(self.ident));
            item.setFailed(True);
            queue.task_done();
            continue;
   

#Parse arguments
parser = argparse.ArgumentParser(description='Download all the Dinosaur Comics from qwantz.com');
parser.add_argument('--start_index', help="which comic to start from", type=int);
parser.add_argument('--comic_dir', help="where to put the comic files", type=str);
parser.add_argument('--num_threads', help="How many threads to download comics with", type=int);
parser.add_argument('--num_comics', help="How many comics to download", type=int);

args = parser.parse_args();

#Arguments and defaults
if args.start_index != None:
   start_index = args.start_index;
else:
   start_index = 1;

if (args.comic_dir != None):
   comic_dir = args.comic_dir;
else:
   comic_dir = 'comics'

if (args.num_threads != None):
   num_threads = int(args.num_threads);
else:
   num_threads = 10;

if (args.num_comics != None):
   num_comics = args.num_comics;
else:
   num_comics = None;

socket.setdefaulttimeout(TIMEOUT);


#make sure that the comics directory exists
if not os.path.exists(comic_dir):
   os.makedirs(comic_dir);

#ImgOpener for saving images
imgopener = urllib.URLopener();
#Queue for managing downloader threads
queue = Queue.Queue();
#urls Array for piecing together title file afterwards
urls = [];

#Nab the archive page to get the URLs
page = urlopen(ARCHIVE_URL);
dom = lxml.html.parse(page);
#grab the ul.archive
def iterate_page(dom):
   index = 0;
   for ul in dom.iter("ul"):
      if (ul.attrib.get("class", False) and ul.attrib['class'] == 'archive'):
         for li in ul.iter("li"):
            for a in li.iter("a"):
               if (COMIC_URL in a.attrib['href']):
                  queueItem = ComicQueueItem();
                  queueItem.setIndex(index);
                  index += 1;
                  queueItem.setPageUrl(a.attrib['href']);

                  urls.append(queueItem);
                  queue.put(queueItem);

                  if (num_comics != None and index > num_comics):
                     return index;

iterate_page(dom);

for thread in range(num_threads):
   t = DownloadComicThread(queue);
   t.setDaemon(True);
   t.start();

queue.join();
   
#create the title_file
title_file = file(comic_dir + "/title_file", "a");
for index in range(len(urls) - 1, -1, -1):
   entry = urls[index];
   if not entry.getFailed():
      title_entry = get_comic_index(entry.getPageUrl()) + "\t" + entry.getPageUrl() + "\t" + entry.getComicUrl() + "\t" + entry.getFilename();
      title_file.write(title_entry + "\n");

title_file.close();
