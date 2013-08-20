#!/usr/bin/python

import math;
import argparse;
import shutil;
import re;
import lxml
from lxml import etree;
from xml.dom import minidom;
from xml.dom.minidom import parse;
import os;
import errno;

argparser = argparse.ArgumentParser(description='Build the downloaded Dinosaur Comics into an epub document');
argparser.add_argument('output', help="What the name of the output directory should be.");
argparser.add_argument('--comic_dir', help="Where the comics and title_file are stored.");
argparser.add_argument('--comic_limit', help="How many comics to put into the output file.");
argparser.add_argument('--comics_per_chapter', help="How many comics should go into a single chapter.");
argparser.set_defaults(comic_dir='comics', comic_limit=False);

args = argparser.parse_args();

if (args.output):
   outdir = args.output;

if (args.comic_dir):
   comic_dir = args.comic_dir;
else:
   comic_dir = 'comics';

if (args.comics_per_chapter):
   comics_per_chapter = int(args.comics_per_chapter);
else:
   comics_per_chapter = 20;

title_file = file(comic_dir + "/title_file", 'r');

template_dir = 'templates';

def get_num_comics():
   if (args.comic_limit):
      return int(args.comic_limit);
   else:
      #Re-reading title file so that it doesn't change the title_file handle
      tf = file(comic_dir + "/title_file", 'r');
      return len(tf.readlines());

def get_num_chapters():
   return int(math.ceil(get_num_comics() / comics_per_chapter));

def pretty_print(element):
   pattern = re.compile("\s*\n");
   pxml = element.toprettyxml();
   return re.sub(pattern, "\n", pxml);

def safe_mkdir(path):
   try:
      os.makedirs(path);
   except OSError as exc:
      if exc.errno == errno.EEXIST and os.path.isdir(path):
         pass;
      else: raise

def safe_copytree(from_path, to_path):
   try:
      shutil.copytree(from_path, to_path);
   except OSError as exc:
      if (exc.errno == errno.EEXIST and os.path.isdir(to_path)):
         pass;
      else:
         raise;

def setup_file_structure():
   safe_mkdir(outdir);
   safe_mkdir(outdir + "/OEBPS");
   safe_mkdir(outdir + "/OEBPS/Text");
   safe_mkdir(outdir + "/OEBPS/Images");
   safe_mkdir(outdir + "/OEBPS/Styles");

def write_meta_inf():
   safe_copytree(template_dir + "/META-INF", outdir + "/META-INF");

def write_mimetype():
   shutil.copy(template_dir + "/mimetype", outdir);

def write_toc_ncx():
   dom = parse(template_dir + "/OEBPS/toc.ncx");

   navmap = dom.getElementsByTagName("navMap")[0];

   for chapter in range(get_num_chapters()):
      navpoint = dom.createElement("navPoint");
      navpoint.attributes['id'] = "navPoint-" + str(chapter);
      navpoint.attributes['playOrder'] = str(chapter + 1);

      navlabel = dom.createElement("navLabel");
      nlt = dom.createElement("text");
      nlt.appendChild(dom.createTextNode("Chapter " + str(chapter)));
      navlabel.appendChild(nlt);

      content = dom.createElement("content");
      content.attributes['src'] = "Text/chapter" + str(chapter) + ".xhtml";

      navpoint.appendChild(navlabel);
      navpoint.appendChild(content);

      navmap.appendChild(navpoint);

   toc = file(outdir + "/OEBPS/toc.ncx", "w");
   toc.write(pretty_print(dom));
   toc.close();

def copy_images():
   title_file.seek(0);

   limit = int(args.comic_limit);
   for line in title_file.readlines():
      entries = line.split("\t");
      if (entries[3].strip() == ""):
         continue;
      shutil.copy(comic_dir + "/" + entries[3].strip(), outdir + "/OEBPS/Images/" + entries[3].strip()); 

      if (args.comic_limit):
         limit -= 1;
         if (limit <= 0):
            break;

def copy_stylesheet():
   shutil.copy(template_dir + "/OEBPS/Styles/stylesheet.css", outdir + "/OEBPS/Styles/stylesheet.css");

def write_content_opf():
   #Parse the template file to use as a baseline
   dom = parse(template_dir + "/OEBPS/content.opf");

   #Populate manifest
   manifest = dom.getElementsByTagName("manifest")[0];
   limit = int(args.comic_limit);
   comics = 0;

   title_file.seek(0);
   for line in title_file.readlines():
      entries = line.split("\t");

      item = dom.createElement("item");
      item.attributes['id'] = "img_" + entries[0];
      item.attributes['href'] = "Images/" + entries[3];
      item.attributes['media-type'] = "image/png";

      manifest.appendChild(item);

      comics += 1;
      if (args.comic_limit):
         limit -= 1;
         if (limit <= 0):
            break;

   chapters = int(math.ceil(comics / comics_per_chapter));
   print(chapters);
   #Add the chapters to the manifest
   for i in range(chapters):
      item = dom.createElement("item");
      item.attributes['id'] = "chapter" + str(i);
      item.attributes['href'] = "Text/chapter" + str(i) + ".xhtml";
      item.attributes['media-type'] = "application/xhtml+xml";
      manifest.appendChild(item);

   #Add chapters to the spine
   spine = dom.getElementsByTagName("spine")[0];
   for i in range(chapters):   
      item = dom.createElement("itemref");
      item.attributes['idref'] = "chapter" + str(i);
      spine.appendChild(item);

   #Write the file
   outfile = file(outdir + "/OEBPS/content.opf", 'w');
   outfile.write(pretty_print(dom));
   outfile.close();
#write_content_opf

def write_page_xhtml():
   #Template dom
   template_dom = parse(template_dir + "/OEBPS/Text/page.xhtml");

   title_file.seek(0);

   if (args.comic_limit):
      n_comics = int(args.comic_limit);
   else:
      n_comics = len(title_file.readlines());
      args.comic_limit = n_comics

   pages = int(math.ceil(n_comics / comics_per_chapter));
   title_file.seek(0);
   next_comic = 0;
   for page in range(pages):
      dom = template_dom.cloneNode(True);
      body = dom.getElementsByTagName("body")[0];

      if (next_comic + comics_per_chapter > args.comic_limit):
         target_comic = args.comic_limit;
      else:
         target_comic =  next_comic + comics_per_chapter;

      for index in range(next_comic, target_comic):
         line = title_file.readline();
         entries = line.split("\t");

         comic = dom.createElement("div");
         comic.attributes["class"] = "comic";
         img = dom.createElement("img");
         img.attributes["src"] = "../Images/" + entries[3];
         #img.attributes["alt"] = entries[3];
         #alt = dom.createElement("p");
         #alt.attributes["class"] = "alt";
         #alt.appendChild(dom.createTextNode(entries[3]));

         comic.appendChild(img);
         #comic.appendChild(alt);

         body.appendChild(comic);
         #/for line in readlines

      next_comic = target_comic;

      #write file
      outfile = file(outdir + "/OEBPS/Text/chapter" + str(page) + ".xhtml", "w");
      outfile.write(pretty_print(dom));
      outfile.close();
   #/for page in pages
#/write_page_xhtml

#Do it
setup_file_structure();
copy_stylesheet();
copy_images();
write_toc_ncx();
write_meta_inf();
write_mimetype();
write_content_opf();
write_page_xhtml();
