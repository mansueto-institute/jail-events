# Illinois Jail Address Geocoding System

A comprehensive geocoding system for Illinois county, municipal, and police department jail addresses. This system uses multiple geocoding APIs and advanced address cleaning to accurately geocode jail facilities across all 102 Illinois counties.

## 🌟 Features

- **Multi-API Geocoding**: Uses OpenStreetMap Nominatim (free) and Here API (premium)
- **Illinois-Specific**: Optimized for Illinois correctional facilities
- **Address Cleaning**: Advanced address normalization and cleaning
- **Fuzzy Matching**: Clusters similar addresses and suggests corrections
- **Comprehensive Database**: Builds a complete Illinois jail database
- **Caching**: Intelligent caching to avoid duplicate API calls
- **Statistics**: Detailed geocoding statistics and quality metrics

## 🏛️ Supported Facility Types

- **County Jails**: Sheriff's department facilities
- **Municipal Jails**: City and town police department jails
- **Juvenile Detention Centers**: Youth correctional facilities
- **Correctional Facilities**: State and federal prisons
- **Police Department Jails**: Temporary holding facilities

## 🚀 Quick Start

### 1. Test the System

```bash
# Test with sample data
uv run python test_illinois_geocoding.py
```

### 2. Geocode Your Data

```bash
# Geocode addresses from your cleaned data
make geocode
```

### 3. Use in Your Code

```python
from jail_events.geocoding.processor import JailAddressProcessor

# Initialize processor
processor = JailAddressProcessor()

# Process your data
df_geocoded = processor.process_jail_addresses(df)

# Get statistics
stats = processor.get_processing_stats(df_geocoded)
```

## 🔧 Configuration

### API Keys (Optional)

For better results, you can use a Here API key:

```python
processor = JailAddressProcessor(
    use_here_api=True,
    here_api_key="your_here_api_key"
)
```

### Similarity Threshold

Adjust the similarity threshold for address clustering:

```python
processor = JailAddressProcessor(similarity_threshold=0.8)
```

## 📊 Output Data

The geocoding system adds the following columns to your data:

- `geocoded_latitude`: Latitude coordinate
- `geocoded_longitude`: Longitude coordinate
- `geocoded_confidence`: Confidence score (0-1)
- `geocoded_method`: Geocoding method used
- `geocoded_formatted_address`: Standardized address
- `facility_type`: Type of facility (county, municipal, etc.)
- `geocoded_county`: County name extracted from address
- `confidence_category`: High/Medium/Low confidence category
- `address_cluster`: Cluster ID for similar addresses
- `suggested_address`: Suggested address correction

## 🌍 Geocoding APIs

### OpenStreetMap Nominatim (Free)
- **Rate Limit**: 1 request per second
- **Coverage**: Global, good for Illinois
- **Cost**: Free
- **Quality**: Good for most addresses

### Here API (Premium)
- **Rate Limit**: Varies by plan
- **Coverage**: Excellent for US addresses
- **Cost**: Pay-per-use
- **Quality**: Very high accuracy

## 📈 Statistics

The system provides comprehensive statistics:

```python
stats = processor.get_processing_stats(df_geocoded)

print(f"Success Rate: {stats['success_rate']:.2%}")
print(f"High Confidence Rate: {stats['high_confidence_rate']:.2%}")
print(f"Average Confidence: {stats['average_confidence']:.2f}")
print(f"Facility Types: {stats['facility_types']}")
print(f"Counties: {stats['counties']}")
```

## 🗂️ File Structure

```
src/jail-events/geocoding/
├── __init__.py
├── address_cleaner.py      # Address cleaning and normalization
├── address_clusterer.py    # Address clustering and suggestions
├── address_geocoder.py     # Main geocoding engine
├── illinois_jails.py       # Illinois jail database
├── jail_locations.py       # Cook County jail locations
└── processor.py            # Main processor
```

## 🔍 Address Cleaning

The system performs comprehensive address cleaning:

1. **Standardization**: Converts to uppercase, standardizes abbreviations
2. **Normalization**: Removes extra spaces, punctuation
3. **Illinois-Specific**: Handles Illinois address patterns
4. **Component Extraction**: Extracts street number, name, city, zip

## 🎯 Clustering

Similar addresses are clustered together:

- **Fuzzy Matching**: Uses Jaro-Winkler distance
- **Threshold-Based**: Configurable similarity threshold
- **Representative Addresses**: Finds best representative for each cluster
- **Suggestions**: Suggests corrections for low-confidence addresses

## 💾 Caching

The system includes intelligent caching:

- **File-Based**: Saves results to JSON file
- **API-Specific**: Separate cache for each API
- **Persistent**: Survives between runs
- **Automatic**: No manual cache management needed

## 🚨 Rate Limiting

The system respects API rate limits:

- **Nominatim**: 1 second delay between requests
- **Here API**: Configurable delays
- **Error Handling**: Graceful handling of rate limit errors
- **Retry Logic**: Automatic retry for temporary failures

## 📋 Example Usage

### Basic Geocoding

```python
from jail_events.geocoding.processor import JailAddressProcessor

# Load your data
df = pl.read_excel("jails_database_with_links.xlsx")

# Initialize processor
processor = JailAddressProcessor()

# Process addresses
df_geocoded = processor.process_jail_addresses(df)

# Export results
processor.export_geocoded_data(df_geocoded, Path("geocoded_data.parquet"))
```

### Advanced Configuration

```python
# With Here API
processor = JailAddressProcessor(
    use_here_api=True,
    here_api_key="your_key_here"
)

# With custom similarity threshold
processor = JailAddressProcessor(similarity_threshold=0.9)
```

### Statistics and Analysis

```python
# Get comprehensive statistics
stats = processor.get_processing_stats(df_geocoded)

# Filter high-confidence results
high_confidence = df_geocoded.filter(pl.col("geocoded_confidence") >= 0.8)

# Group by facility type
by_type = df_geocoded.group_by("facility_type").agg([
    pl.count().alias("count"),
    pl.col("geocoded_confidence").mean().alias("avg_confidence")
])
```

## 🐛 Troubleshooting

### Common Issues

1. **Rate Limiting**: Increase delays between API calls
2. **Low Confidence**: Check address formatting and try different APIs
3. **Missing Results**: Verify addresses are in Illinois
4. **Cache Issues**: Delete cache file to start fresh

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 API Documentation

### OpenStreetMap Nominatim
- [Nominatim API Documentation](https://nominatim.org/release-docs/develop/api/Overview/)
- [Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)

### Here API
- [Here Geocoding API](https://developer.here.com/documentation/geocoding-search-api/dev_guide/topics/endpoint-geocode-brief.html)
- [Rate Limits](https://developer.here.com/documentation/geocoding-search-api/dev_guide/topics/rate-limits.html)

## 🤝 Contributing

To add new geocoding APIs or improve address cleaning:

1. Add new geocoder to `address_geocoder.py`
2. Update `processor.py` to use new geocoder
3. Add tests to `test_illinois_geocoding.py`
4. Update this README

## 📄 License

This geocoding system is part of the jail-events project and follows the same license terms.

## 🆘 Support

For issues or questions:

1. Check the troubleshooting section
2. Review the test script for examples
3. Check API documentation for rate limits
4. Verify your addresses are properly formatted

---

**Note**: This system is designed specifically for Illinois correctional facilities. For other states or countries, you may need to modify the address cleaning patterns and geocoding context.
