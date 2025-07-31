# Extraction of Illinois Jail Event Reports

By Mansueto Institute Data Journalism Fellows Andrés Comacho and Ganon Evans

## Background

Illinois county, municipal, and police department jails are required to report Extraordinary or Unusual Occurrences to the Illinois Department of Corrections. These reports include a wide range of topics, including battery, assault, self-harm, restaint and OC spray usage, deaths, and an "Other" category jails have used for topics like contraband. The reports traditionally consist of 2-3 pages, with the first as a summary sheet of what the occurrence was with some basic information like its location, date, and injuries. The second and third pages consist of write-ups of the specifics of the report by jail staff with a section for areas for improvement.

The Better Government Association and Illinois Answers Project made numerous Freedom of Information Act (FOIA) requests to the Illinois Department of Corrections to receive these reports dating back to the mid-2010s. The reports were sent in varying PDF forms. Some reports were electronically produced, with others being scanned or even handwritten. The vast majority of received reports consisted of just the front page.

Given that these reports had never been digitalized, we wanted to scrape the information from them to answer basic questions like how frequent different occurrences across counties. Similarly, processing the reports allows for things like identifying unusual events for further investigation.

The original batch of reports consisted of 26,909 reports, but this program can be used with future samples as well. 

## Overview

The app has three primary processes, an overview of each of which are below:

1. **Preprocess** - Turns a PDF into an image, adjusts the page to account for angled text or distorted format, and then crops the image after finding the title at the top of the page as well as the footnotes at the bottom. Each image will have a width of 2500 pixels and a height of 3300 pixels. Ideally, the image is bounded by the title and footnotes. Images without the report title are removed from the pipeline, as they're additional documents sent with the report or emails from the FOIA process. 

1. **PDF Processing** - As images, pixel coordinates are used on the reports to define regions of interest (ROI) for fields of the report so they can be extracted via OCR. The correct coordinates for each report depend on the report version, of which there were 4 we accounted for: 2002, 2016, 2024, and Cook County. We get the report version from doing an initial extraction of the bottom right corner and finding the year. Cook County forms are listed as the 2016 version, so we do an initial extraction of the facility name to see if it contains "Cook County." The importance of identifying Cook County comes with parsing the Detainee table and information after it.

    To extract the facility name, address, phone number, date, time, RD Number, deceased name, cause of death, date and time of death, and death reporter, we use image to text conversion based on coordinate. For most reports, the sections involving a death will remain empty or with variables like "NA", but we still pull the text here to confirm with confidence there was a death. 

    To extract facility type, AM or PM, the question "Any resulting death?", and the question about being suicide watch, we identify the checkboxes from the polygons on the page, calculate how filled each checkbox is, then take the most filled checkbox and the least filled checkbox and ask if the most filled is more filled than the least filled by a given ratio for each section. For injuries and the last two deceased questions about physician examination and illness, we perform a similar box check to above except if there's a filled box found, we pull a longer amount of text after the box to account for the blanks. In the checkbox process, we exclude bad parses of supposed checkboxes, including checkboxes with high or low aspect ratios and zero area.

    To process the occurrence section, we do a largescale initial scan for checkboxes amongst the polygons with controls to prevent clustered letters from being misidentified. Each checkbox is stored in a dictionary with the key being the coordinates of the checkbox and the values containing the fill ratio of the checkbox and the text after it. Using coordinates, we take a longer region of text for "Other" and the "Suicide" occurrences to account for written text. From, we take all of the fill ratios, calculate the average, then decide that a checkbox is filled if its fill ratio is equal to or greater than 150% of the average. We do this different calculation to account for the fact that multiple checkboxes can be filled. In a random sample of 100 reports, we correctly identified all occurrences in 95 reports, with 2 of the others being handwritten and the other three being poor quality. Of a sample of 209 reports on restraint usage, we correctly identified all occurrences in 207 of the reports. The final return from this process is a list of occurrences corresponding to filled checkboxes.

    To parse the Detainees Involved table, we identify an ROI then use kernels to identify long vertical and horizontal lines. While keeping long lines that would be found in letters, such as "h" or "l", we remove the lines of the table, leaving just the remaining text. We perform an extraction of all of the text there then excluded text based on fuzzy matching to the table headers and length. This does an initial exclusion of "hallucinations" common in the extraction.

    In the 2002, 2016, and 2024 forms, the table is always four rows. However, for Cook County, the table varies with the number of detainees involved, ranging from 1 to more than 20. Depending on the length of the page, information on injuries and deaths may be higher up or farther down - sometimes pushed onto a second page. To account for this, in Cook County reports, we define a large ROI and then have to first find the lowest horiztonal line of the table. We then cut off the ROI at this line and perform table extraction as above. Then, coordinates for injuries and the death statistics are calculated for the rest of the report. 

    Each report produces a dictionary with its fields, which are used to produce a Parquet file of all reports. At this time, an OCR confidence score is produced. Reports with a score less than 80 are marked as handwritten due to their quality, thus necessitating individual analysis.

1. **Cleaning** - The Parquet file of all reports has basic cleaning to its fields to isolate information from hallucinations or extra characters from OCR extraction. Similar county entries are combined. 

At this time, the extraction of the detainee table are fed into the Hugging Face Named Entity Recognition (NER) model to identify names, which are then use to create a database of reports by individual. The NER uses 334 Million parameters that leverages both local and global contexts. We achieve an F1 Score of 92-93% with the person entity class. This means it correctly identifies person names with very high precision (few false positives) and recall (few missed names) in typical English text.

The Parquet files by report and by individual are exported as Excel sheets. 

## Methodological Overview

Pulling information from the reports involves Optical Character Recognition using the Tesseract engine. The OCR tool turns the image's contents into a series of black and white dots then, whose pitch, shape, and proportions are compared to a dataset of fonts and other text samples. 

In order to improve the parse quality in some examples, we use OpenCV to modify the the ROI we pass to the scanning functions. Specifically, we use a kernel to erode and redilate the contours so that they have sharper edges. This is useful for getting more distinct letters or edges when identifying checkboxes.

We use OpenCV's polygon approximation tools to identify square-like shapes then do checks on area and shape to confirm. We then calculate a fill ration of the pixels and use it as a comparison against other found boxes.

## How to run

