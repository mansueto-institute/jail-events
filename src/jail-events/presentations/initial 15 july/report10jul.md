<div align="center">

# Jail Events Data Processing Report

![Insistute](https://img.shields.io/badge/Institution-Mansueto%20Institute-yellow)
![University](https://img.shields.io/badge/University-Chicago-maroon)

**Date:** July 10, 2025
</div>

---

<div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px;">
<div style="text-align: justify; margin-bottom: 30px;">

## Executive Summary  
1. Total pages processed
2. Handwritten analysis: successfully extracted with high confidence
3. Cleaning progress and missing values
4. Facilities identified and time trends
5. Facility coverage for all reports
6. Extraction of samples to Excel 



<div style="background-color:rgb(255, 255, 255); padding: 20px; border-radius: 8px; margin: 20px 0;">


## 1. Total pages processed

| status  | Count | Percentage |
|---------|-------|------------|
| success | 27333 | 98.0       |
| failed  | 559   | 2.0        |

**Total Documents Processed:** 27,892

</div>
</div>

<div style="text-align: justify; margin: 20px 0;">

## 2. Handwritten Analysis

![OCR Distribution](images/ocr_distribution.png)

Total documents with OCR Confidence < 80: 857
(likely handwritten)

A sample of them: 

![Handwritten](images/samplehandwr.png)

## 3. Cleaning progress and missing values
 
![facilities](images/facilitiynames.png)
![dates](images/datesclean.png)


| Field        | Total | Missing | Missing_Percent |
|--------------|-------|---------|-----------------|
| Cleaned Date | 27333 | 5431    | 19.869755       |
| Cleaned Facility Name | 27333 | 2239    | 8.191563        |


## 4. Facilities identified and time trends

![Top Facilities](images/top_facilities.png)
![Cases Over Time](images/cases_over_time.png)

## 5. Facility coverage for all reports

Facility Coverage Analysis (2018-2024):

**Top 20 Facilities by Month Coverage**

| Cleaned Facility Name           | Months_With_Data | Total_Records |
|---------------------------------|------------------|---------------|
| Madison County Sheriffs Office  | 81               | 1222          |
| Sangamon County Jail            | 80               | 633           |
| Kane County Sheriffs Office     | 77               | 1485          |
| Lake County Jail                | 77               | 1133          |
| Sangamon County Adult Detentio… | 74               | 256           |
| Macon County Jail               | 73               | 326           |
| Dupage County Jail              | 72               | 392           |
| Peoria County Sheriffs Office   | 67               | 504           |
| Lake County Adult Corrections   | 64               | 284           |
| Williamson County Jail          | 64               | 210           |
| St Clair County Sheriffs Depar… | 60               | 380           |
| Will County Adult Detention Fa… | 60               | 145           |
| Mchenry County Adult Correctio… | 56               | 225           |
| Macoupin County Sheriff         | 56               | 134           |
| Lake County Sheriffs Office     | 53               | 126           |
| Tazewell County Jail            | 50               | 200           |
| Coles County Safety Detention … | 48               | 118           |
| Stephenson County Jail          | 48               | 112           |
| Winnebago County Jail           | 48               | 102           |
| Peoria County Jail              | 46               | 164           |

(complete data set on box folder)

## 6. Extraction of samples to Excel

From a sample of 395 pages:
- Cleanned date
- Occurences

(Box shared folder)

| Cleaned Occurrences             | count |
|---------------------------------|-------|
| Serious Injury,Fighting among … | 76    |
| Serious Injury,OC Spray Used,B… | 67    |
| Restraints Used                 | 26    |
| Serious Injury,Fighting among … | 16    |
| Serious Injury,OC Spray Used,S… | 14    |
| Fighting among Detainees        | 12    |
| Error, no occurrence found      | 11    |
| OC Spray Used                   | 8     |
| Serious Injury,Fighting among … | 6     |
| Serious Injury,OC Spray Used,O… | 4     |

- Facility name

| Cleaned Facility Name           | count |
|---------------------------------|-------|
| Cook County Department Of Corr… | 204   |
| null                            | 22    |
| Madison County Sheriffs Office  | 21    |
| Lake County Jail                | 20    |
| Sangamon County Jail            | 15    |
| Sangamon County Adult Detentio… | 12    |
| Lake County Adult Corrections   | 8     |
| Peoria County Sheriffs Office   | 7     |
| Kane County Sheriffs Office     | 7     |
| St Clair County Sheriffs Depar… | 6     |

- Names from table 

| Inmate Names                    | count |
|---------------------------------|-------|
|                                 | 97    |
| Clinton Cou                     | 2     |
| Malique D Clark                 | 2     |
| Scott Timothy D                 | 2     |
| Kyle Wunderlich                 | 2     |
| Abels Kristin                   | 1     |
| Michael A Aguirre               | 1     |
| Devin Aldridge,Alphonso W Joyn… | 1     |
| Nathaniel T Alexander,Michael … | 1     |
| Nathaniel T Alexander           | 1     |

</div>
</div>