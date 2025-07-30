# Extraction of Illinois Jail Event Reports

## Background

Illinois county, municipal, and police department jails are required to report Extraordinary or Unusual Occurrences to the Illinois Department of Corrections. These reports include a wide range of topics, including battery, assault, self-harm, restaint and OC spray usage, deaths, and an "Other" category jails have used for topics like contraband. The reports traditionally consist of 2-3 pages, with the first as a summary sheet of what the occurrence was with some basic information like its location, date, and injuries. The second and third pages consist of write-ups of the specifics of the report by jail staff with a section for areas for improvement.

The Better Government Association and Illinois Answers Project made numerous Freedom of Information Act (FOIA) requests to the Illinois Department of Corrections to receive these reports dating back to the mid-2010s. The reports were sent in varying PDF forms. Some reports were electronically produced, with others being scanned or even handwritten. The vast majority of received reports consisted of just the front page.

Given that these reports had never been digitalized, we wanted to scrape the information from them to answer basic questions like how frequent different occurrences across counties. Similarly, processing the reports allows for things like identifying unusual events for further investigation.

## Overview

The app consists of the following different pieces:

1. **Preprocess** - Turns a PDF into an image, adjusts the page to account for angled text or distorted format, and then crops the image after finding the title at the top of the page. Images without the report title are removed from the pipeline. 

1. **PDF Processing** - As images, pixel coordinates are used on the reports to define regions of interest (ROI) for fields of the report so they can be extracted via OCR. Methods include, direct text extraction, identifying filled checkboxes and extracting corresponding text, and processing information in a table. Each report produces a dictionary with its fields, which are used to produce a Parquet file of all reports. At this time, an OCR confidence score is produced. Reports with a score less than 80 are marked as handwritten due to their quality, thus necessitating individual analysis.

1. **Cleaning** - The Parquet file of all reports has basic cleaning to its fields to isolate information from hallucinations or extra characters from OCR extraction. Similar county entries are combined. At this time, the extraction of the detainee table are fed into the Hugging Face Named Entity Recognition (NER) model to identify names, which are then use to create a database of reports by individual. 

## Methodological overview

Pulling information from the reports involves Optical Character Recognition using the Tesseract engine. The OCR tool turns the image's contents into a series of black and white dots then, whose pitch, shape, and proportions are compared to a dataset of fonts and other text samples. 

In order to improve the parse quality in some examples, we use OpenCV to modify the the ROI we pass to the scanning functions. Specifically, we use a kernel to erode and redilate the contours so that they have sharper edges. This is useful for getting more distinct letters or edges when identifying checkboxes.

We use OpenCV's polygon approximation tools to identify square-like shapes then do checks on area and shape to confirm. We then calculate a fill ration of the pixels and use it as a comparison against other found boxes.

## How to run

