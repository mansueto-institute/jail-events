# Unified Illinois Jail Database System

A comprehensive system for building, geocoding, and matching Illinois jail facilities with your existing data. Perfect for creating dashboards with accurate mapping and spatial analysis.

## 🎯 **What This System Does**

1. **Builds Illinois Jail Database** - Scrapes official sources for all Illinois county, municipal, and police department jails
2. **Geocodes with OSM** - Gets accurate coordinates using OpenStreetMap Nominatim API
3. **Fuzzy Matches Your Data** - Links your existing jail events data with the Illinois database
4. **Creates Unified Database** - Combines everything for dashboard and analysis

## 🏗️ **System Architecture**

```
Official Illinois Sources → Illinois Database → OSM Geocoding → Coordinates
                                                      ↓
Your Jail Events Data → Fuzzy Matching → Matched Data
                                                      ↓
                    Unified Database → Dashboard Ready
```

## 🚀 **Quick Start**

### 1. Test the System
```bash
cd src/jail-events
uv run python test_unified_illinois.py
```

### 2. Process Your Real Data
```bash
make illinois-db
```

### 3. Check Results
```bash
ls -la data/illinois_jail_analysis/
```

## 📊 **Output Files**

The system creates several files in `data/illinois_jail_analysis/`:

- **`illinois_jails_database.parquet`** - Complete Illinois jail database with coordinates
- **`jail_events_with_coordinates.parquet`** - Your data matched with coordinates
- **`unified_illinois_jails.parquet`** - Combined database for analysis
- **`illinois_jails_for_dashboard.xlsx`** - Excel file ready for dashboard creation

## 🏛️ **Illinois Jail Database**

### **Coverage**
- **102 Illinois Counties** - All county sheriff jails
- **Municipal Jails** - City and town police department jails
- **Juvenile Facilities** - Youth detention centers
- **Correctional Facilities** - State and federal prisons

### **Data Fields**
- `name` - Facility name
- `official_name` - Official government name
- `address` - Street address
- `city` - City name
- `county` - County name
- `facility_type` - Type (county/municipal/juvenile/correctional)
- `latitude` / `longitude` - Coordinates
- `phone` - Contact number
- `capacity` - Facility capacity
- `geocoded_confidence` - Geocoding confidence score

## 🔗 **Data Matching**

### **Fuzzy Matching Algorithm**
1. **Address Similarity** - Uses Jaro-Winkler distance (70% weight)
2. **Name Similarity** - Matches facility names (30% weight)
3. **Threshold** - Minimum 70% similarity for matches
4. **Fallback** - OSM geocoding for unmatched addresses

### **Match Results**
- `illinois_jail_id` - Matched Illinois database ID
- `illinois_latitude` / `illinois_longitude` - Coordinates from Illinois DB
- `match_confidence` - Match confidence score
- `match_method` - How the match was made

## 📈 **Statistics & Quality**

The system provides comprehensive statistics:

```python
# Example statistics output
{
    'illinois_database': {
        'total_facilities': 150,
        'geocoded_facilities': 145,
        'county_jails': 102,
        'municipal_jails': 30,
        'juvenile_facilities': 18
    },
    'matched_data': {
        'total_records': 5000,
        'successfully_matched': 4200,
        'match_rate': 0.84
    }
}
```

## 🗺️ **Dashboard Integration**

### **Excel File Structure**
The `illinois_jails_for_dashboard.xlsx` file contains:
- All Illinois jails with coordinates
- Your matched data with coordinates
- Facility types and counties
- Confidence scores for quality control

### **Mapping Ready**
- **Latitude/Longitude** - Ready for mapping libraries
- **County Information** - For county-level analysis
- **Facility Types** - For filtering and categorization
- **Confidence Scores** - For quality filtering

## 🔧 **Configuration**

### **Geocoding Settings**
```python
# Rate limiting
time.sleep(1.1)  # Nominatim: 1 request/second

# Similarity thresholds
address_threshold = 0.7  # Minimum address similarity
name_threshold = 0.7     # Minimum name similarity
```

### **Cache Management**
- **Geocoding Cache** - `geocoding_cache.json`
- **Illinois Database** - `illinois_jail_cache/illinois_jails_database.parquet`
- **Automatic Updates** - Rebuilds when data changes

## 📋 **Usage Examples**

### **Basic Usage**
```python
from geocoding.unified_processor import process_illinois_jail_data

# Process all data
results = process_illinois_jail_data("path/to/your/data.xlsx")

# Access results
illinois_db = results['illinois_database']
matched_data = results['matched_data']
unified_db = results['unified_database']
```

### **Custom Processing**
```python
from geocoding.illinois_database_builder import IllinoisJailDatabaseBuilder

# Build Illinois database only
builder = IllinoisJailDatabaseBuilder()
illinois_db = builder.build_comprehensive_database()

# Match with your data
matched_data = builder.match_with_existing_data(illinois_db, your_data)
```

## 🎯 **Dashboard Use Cases**

### **1. Interactive Maps**
- Plot all Illinois jails on a map
- Color-code by facility type
- Filter by county or region
- Show capacity and other attributes

### **2. Spatial Analysis**
- Distance calculations between facilities
- Coverage analysis by county
- Population density vs. jail capacity
- Regional clustering analysis

### **3. Data Quality**
- Identify unmatched facilities
- Flag low-confidence matches
- Track geocoding accuracy
- Monitor data completeness

## 🔍 **Quality Control**

### **Geocoding Quality**
- **High Confidence** (≥0.8) - Very reliable coordinates
- **Medium Confidence** (0.6-0.8) - Good coordinates, may need verification
- **Low Confidence** (<0.6) - Coordinates may be inaccurate

### **Matching Quality**
- **Exact Match** - Perfect address and name match
- **Fuzzy Match** - Similar address/name with high confidence
- **No Match** - No suitable match found

### **Verification Steps**
1. Check high-confidence matches for accuracy
2. Review medium-confidence matches manually
3. Investigate unmatched facilities
4. Update database with corrections

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Low Geocoding Success**
   - Check address formatting
   - Verify addresses are in Illinois
   - Check API rate limits

2. **Poor Matching Results**
   - Adjust similarity thresholds
   - Improve address cleaning
   - Add more Illinois database entries

3. **Missing Facilities**
   - Add to Illinois database manually
   - Check official sources
   - Update database regularly

### **Debug Mode**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 **Data Sources**

### **Official Sources**
- Illinois Department of Corrections
- County Sheriff's Offices
- Municipal Police Departments
- University of Chicago Crime Lab

### **Geocoding APIs**
- OpenStreetMap Nominatim (Primary)
- Here API (Optional, premium)

## 🔄 **Maintenance**

### **Regular Updates**
1. **Monthly** - Check for new facilities
2. **Quarterly** - Update coordinates
3. **Annually** - Full database review

### **Data Validation**
- Cross-reference with official sources
- Verify coordinates accuracy
- Update facility information
- Remove closed facilities

## 📞 **Support**

For issues or questions:
1. Check the troubleshooting section
2. Review the test script for examples
3. Check API documentation
4. Verify your data format

## 🎉 **Success Metrics**

A successful run should show:
- **90%+ geocoding success** for Illinois database
- **80%+ matching success** for your data
- **Complete coverage** of all 102 Illinois counties
- **High confidence scores** for most matches

---

**Ready to build your Illinois jail dashboard? Run `make illinois-db` and start mapping!** 🗺️
