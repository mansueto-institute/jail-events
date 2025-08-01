# Extraction of Illinois Jail Event Reports

<div align="center">
  <img src="https://mansueto.uchicago.edu/wp-content/uploads/2019/09/mansueto-logo-horizontal.png" alt="Mansueto Institute Logo" width="400">
</div>


By Mansueto Institute Data Journalism Fellows Andrés Comacho and Ganon Evans

## Background

Illinois county, municipal, and police department jails are required to report Extraordinary or Unusual Occurrences to the Illinois Department of Corrections. These reports include a wide range of topics, including battery, assault, self-harm, restaint and OC spray usage, deaths, and an "Other" category jails have used for topics like contraband. The reports traditionally consist of 2-3 pages, with the first as a summary sheet of what the occurrence was with some basic information like its location, date, and injuries. The second and third pages consist of write-ups of the specifics of the report by jail staff with a section for areas for improvement.

The Better Government Association and Illinois Answers Project made numerous Freedom of Information Act (FOIA) requests to the Illinois Department of Corrections to receive these reports dating back to the mid-2010s. The reports were sent in varying PDF forms. Some reports were electronically produced, with others being scanned or even handwritten. The vast majority of received reports consisted of just the front page.

Given that these reports had never been digitalized, we wanted to scrape the information from them to answer basic questions like how frequent different occurrences across counties. Similarly, processing the reports allows for things like identifying unusual events for further investigation.

The original batch of reports consisted of 26,909 reports, but this program can be used with future samples as well. 

## Overview

The app has three primary processes, an overview of each of which are below:

1. **Preprocess** - This stage transforms PDF pages into standardized, analysis-ready images through a multi-step pipeline designed to handle the varied quality and formatting of scanned jail reports. The process begins by converting each PDF page to a high-resolution image (300 DPI) using PyMuPDF, followed by automatic orientation correction to ensure all documents are in portrait format. The pipeline then employs Hough line detection to identify and correct document skew using median angle calculations from detected lines. A critical component is the intelligent title detection system that uses OCR to locate the "REPORT EXTRAORDINARY UNUSUAL" keyword within the top 20% of the document, allowing the system to crop out extraneous headers, scanner artifacts, and FOIA-related materials that don't contain report data. This title-based cropping ensures that only the actual report content proceeds through the pipeline.

The standardization phase uses image analysis techniques to create consistent output dimensions and positioning across all reports. The system employs statistical analysis of pixel intensity distributions using Polars DataFrames to identify content boundaries, applying rolling median filters to smooth out noise and detect meaningful content edges. Auto-cropping algorithms remove variable scanner borders by identifying the darkest pixel boundaries, while maintaining configurable margins around detected content. The final output is a precisely sized image (2550×3300 pixels) with content positioned at consistent coordinates, enabling reliable OCR extraction in subsequent processing steps. This standardization is crucial for the coordinate-based field extraction system, as it ensures that facility names, dates, checkbox locations, and table structures appear in predictable positions across all four report versions (2002, 2016, 2024, and Cook County formats).

1. **PDF Processing** - As images, pixel coordinates are used on the reports to define regions of interest (ROI) for fields of the report so they can be extracted via OCR. The correct coordinates for each report depend on the report version, of which there were 4 we accounted for: 2002, 2016, 2024, and Cook County. We get the report version from doing an initial extraction of the bottom right corner and finding the year. Cook County forms are listed as the 2016 version, so we do an initial extraction of the facility name to see if it contains "Cook County." The importance of identifying Cook County comes with parsing the Detainee table and information after it.

    To extract the facility name, address, phone number, date, time, RD Number, deceased name, cause of death, date and time of death, and death reporter, we use image to text conversion based on coordinate. For most reports, the sections involving a death will remain empty or with variables like "NA", but we still pull the text here to confirm with confidence there was a death. 

    To extract facility type, AM or PM, the question "Any resulting death?", and the question about being suicide watch, we identify the checkboxes from the polygons on the page, calculate how filled each checkbox is, then take the most filled checkbox and the least filled checkbox and ask if the most filled is more filled than the least filled by a given ratio for each section. For injuries and the last two deceased questions about physician examination and illness, we perform a similar box check to above except if there's a filled box found, we pull a longer amount of text after the box to account for the blanks. In the checkbox process, we exclude bad parses of supposed checkboxes, including checkboxes with high or low aspect ratios and zero area.

    To process the occurrence section, we do a largescale initial scan for checkboxes amongst the polygons with controls to prevent clustered letters from being misidentified. Each checkbox is stored in a dictionary with the key being the coordinates of the checkbox and the values containing the fill ratio of the checkbox and the text after it. Using coordinates, we take a longer region of text for "Other" and the "Suicide" occurrences to account for written text. From, we take all of the fill ratios, calculate the average, then decide that a checkbox is filled if its fill ratio is equal to or greater than 150% of the average. We do this different calculation to account for the fact that multiple checkboxes can be filled. In a random sample of 100 reports, we correctly identified all occurrences in 95 reports, with 2 of the others being handwritten and the other three being poor quality. Of a sample of 209 reports on restraint usage, we correctly identified all occurrences in 207 of the reports. The final return from this process is a list of occurrences corresponding to filled checkboxes.

    To parse the Detainees Involved table, we identify an ROI then use kernels to identify long vertical and horizontal lines. While keeping long lines that would be found in letters, such as "h" or "l", we remove the lines of the table, leaving just the remaining text. We perform an extraction of all of the text there then excluded text based on fuzzy matching to the table headers and length. This does an initial exclusion of "hallucinations" common in the extraction.

    In the 2002, 2016, and 2024 forms, the table is always four rows. However, for Cook County, the table varies with the number of detainees involved, ranging from 1 to more than 20. Depending on the length of the page, information on injuries and deaths may be higher up or farther down - sometimes pushed onto a second page. To account for this, in Cook County reports, we define a large ROI and then have to first find the lowest horiztonal line of the table. We then cut off the ROI at this line and perform table extraction as above. Then, coordinates for injuries and the death statistics are calculated for the rest of the report. 

    Each report produces a dictionary with its fields, which are used to produce a Parquet file of all reports. At this time, an OCR confidence score is produced. Reports with a score less than 80 are marked as handwritten due to their quality, thus necessitating individual analysis.

1. **Cleaning** - The Parquet file of all reports has basic cleaning to its fields to isolate information from hallucinations or extra characters from OCR extraction. Similar county entries are combined. 

At this time, the extraction of the detainee table are fed into the Hugging Face Named Entity Recognition (NER) model to identify names, which are then use to create a database of reports by individual. The NER uses 334 Million parameters that leverages both local and global contexts. The model reports an F1 Score of 92-93% with the person entity class on trained data. This means it correctly identifies person names with very high precision (few false positives) and recall (few missed names) in typical English text.

The Parquet files by report and by individual are exported as Excel sheets and in each row it is included a link to the specific image as part of the database.

## Methodological Overview

Pulling information from the reports involves Optical Character Recognition using the Tesseract engine. The OCR tool turns the image's contents into a series of black and white dots then, whose pitch, shape, and proportions are compared to a dataset of fonts and other text samples. 

In order to improve the parse quality in some examples, we use OpenCV to modify the the ROI we pass to the scanning functions. Specifically, we use a kernel to erode and redilate the contours so that they have sharper edges. This is useful for getting more distinct letters or edges when identifying checkboxes.

We use OpenCV's polygon approximation tools to identify square-like shapes then do checks on area and shape to confirm. We then calculate a fill ration of the pixels and use it as a comparison against other found boxes.

## How to run

Before running the project, ensure your directory structure matches the following:

```
jail-events/
├── src/
│   └── jail-events/
│       ├── main.py                    # Main execution script
│       ├── utils.py                   # Utility functions for PDF processing
│       ├── cleaning/                  # Data cleaning pipeline
│       ├── preprocess/                # Image preprocessing pipeline
│       └── pdf_processing/            # OCR and field extraction
│
├── data/
│   └── jails-data/
│       ├── raw/                       # Place your PDF files here
│       │   ├── report1.pdf
│       │   ├── report2.pdf
│       │   └── ...
│       ├── samples/                   # Sample PDFs for testing
│       │   └── debug/                 # Debug folder for trickier pdfs
│       ├── processed/                 # Processed images (auto-created)
│       └── output/                    # Final parquet and Excel files (auto-created)
├── pyproject.toml
└── README.md
```

Running the program requires installation of the Tesseract software. [Instructions on doing so can be found here.](https://tesseract-ocr.github.io/tessdoc/Installation.html)


### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/jail-events.git
   cd jail-events
   ```

2. **Install all dependencies with uv:**
   ```bash
   uv sync
   ```
   This will automatically install Python 3.12+, Tesseract OCR, and all required Python packages defined in `pyproject.toml`.

### Data Setup

1. **Create the data directory structure:**
   ```bash
   mkdir -p data/jails-data/{raw,samples,processed,output}
   ```

2. **Add your PDF files:**
   - Place all PDF reports in `data/jails-data/raw/` for full processing
   - Place sample PDFs in `data/jails-data/samples/` for testing

### Running the Pipeline

Navigate to the source directory and run the main script:

```bash
cd src/jail-events
uv run main.py [OPTIONS]
```

**Available options:**

- `--mode`: Choose processing mode
  - `full`: Process all PDFs in raw folder (~27,800 pages)
  - `sample`: Process sample PDFs (~642 pages)
  - `debug`: Process a few problematic pages for debugging

- `--step`: Choose pipeline step
  - `all`: Run complete pipeline (parse → clean → export)
  - `parse`: Only convert PDFs to structured data
  - `clean`: Only clean existing parsed data
  - `export`: Only export cleaned data to Excel

**Example commands:**

```bash
# Run complete pipeline on sample data
uv run main.py --mode sample --step all

# Only parse PDFs from raw folder
uv run main.py --mode full --step parse

# Export cleaned data to Excel
uv run main.py --step export
```

### Output Files

The pipeline generates several output files in `data/jails-data/output/`:

- `jails_pdfs_[mode].parquet`: Raw extracted data
- `jails_pdfs_cleaned.parquet`: Cleaned page-level data
- `jails_person_records.parquet`: Person-level data with NER
- `jails_database_with_links.xlsx`: Excel file with hyperlinks to images
- `processing_logs_[mode].parquet`: Processing error logs

### Automated Analysis and Presentation

The project includes an automated Quarto presentation that generates visualizations and analysis from the processed data:

**Location:** `src/jail-events/presentations/final_presentation/pr_29jul.qmd`

**Features:**
- Interactive charts showing occurrence patterns across facilities
- Time series analysis of report frequency
- Facility coverage and data completeness statistics
- Restraint usage analysis by jail
- Death reports summary and investigation findings
- Person-level dataset statistics and name frequency analysis

**To generate the presentation:**
```bash
cd src/jail-events/presentations/final_presentation
quarto render pr_29jul.qmd
```

This will create an interactive HTML presentation with:
- Summary statistics of 27,892 processed pages
- Analysis of 78 confirmed deaths across Illinois jails  
- Occurrence frequency patterns (restraints, suicide attempts, etc.)
- Facility-by-facility breakdowns with interactive visualizations
- Data quality metrics and processing confidence scores

The presentation automatically updates when new data is processed, making it easy to generate reports for different time periods or facility subsets.


### Troubleshooting

- **Import errors:** Ensure you're running from the `src/jail-events` directory
- **OCR errors:** Run `uv sync` again to ensure Tesseract is properly installed
- **Memory issues:** Use `--mode sample` for testing with smaller datasets
- **Processing failures:** Check the processing logs for specific error details