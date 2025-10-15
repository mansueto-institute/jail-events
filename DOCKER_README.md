# Jail Events Processing Pipeline

This project processes Illinois Jail Event reports using OCR and machine learning techniques to extract structured data from PDF documents.

## Quick Start with Docker + Make

### Prerequisites
- Docker and Docker Compose
- Make (optional, but recommended for easy commands)

### Available Commands

```bash
# Build the Docker image
make build

# Run the full pipeline on all data
make full-pipeline

# Run pipeline on sample data (faster for testing)
make sample-pipeline

# Run pipeline on debug data (smallest dataset)
make debug-pipeline

# Run handwritten analysis only (uses cached cleaned data if available)
make handwritten-pipeline

# Force handwritten analysis using cached cleaned data (much faster)
make handwritten-cached

# Run individual steps
make parse-only    # Only parse PDFs
make clean-only    # Only clean data
make export-only   # Only export to Excel

# Development
make install-deps  # Install dependencies locally
make test         # Run tests

# Cleanup
make clean        # Remove containers and images
```

### Manual Docker Commands

If you prefer using Docker directly:

```bash
# Build image
docker-compose build

# Run full pipeline
docker-compose run --rm pipeline

# Run handwritten analysis
docker-compose run --rm handwritten

# Run with custom parameters
docker-compose run --rm jail-events python -m jail-events.main --mode sample --step parse
```

## Processing Modes

### Full Mode (`--mode full`)
- Processes all ~27,800 pages from raw PDFs
- Most comprehensive but slowest
- Use: `make full-pipeline`

### Sample Mode (`--mode sample`)
- Processes ~642 pages from sample PDFs
- Good for testing and development
- Use: `make sample-pipeline`

### Debug Mode (`--mode debug`)
- Processes a few problematic pages
- Fastest for debugging
- Use: `make debug-pipeline`

### Handwritten Mode (`--mode handwritten`)
- Processes only handwritten documents (OCR confidence < 80)
- Creates separate Excel file with handwritten documents
- Use: `make handwritten-pipeline`

## Pipeline Steps

### Parse (`--step parse`)
- Converts PDFs to images
- Extracts text using OCR
- Calculates OCR confidence scores
- Outputs: `jails_pdfs_*.parquet`

### Clean (`--step clean`)
- Cleans facility names, addresses, dates
- Standardizes occurrence types
- Extracts person records
- Outputs: `jails_pdfs_cleaned.parquet`, `jails_person_records.parquet`

### Export (`--step export`)
- Creates Excel files with hyperlinks to images
- Outputs: `jails_database_with_links.xlsx`

### Handwritten (`--step handwritten`)
- **Smart Processing**: Uses `jails_person_records.parquet` as reference for what's been processed
- Identifies handwritten pages (OCR < 80) missing from person records
- Processes only missing handwritten documents through cleaning pipeline
- Creates Excel file with same fields as main database
- Outputs: `handwritten_party/handwritten_documents.xlsx`
- **Performance**: ~5-15 minutes (depends on missing handwritten document count)

## Output Files

### Main Outputs
- `jails_pdfs_cleaned.parquet` - Cleaned main database
- `jails_person_records.parquet` - Individual person records
- `jails_database_with_links.xlsx` - Excel file with hyperlinks

### Handwritten Outputs
- `handwritten_party/handwritten_cleaned.parquet` - Cleaned handwritten documents
- `handwritten_party/handwritten_documents.xlsx` - Excel file with handwritten documents

## Data Structure

```
src/jail-events/data/jails-data/
├── raw/                    # Original PDF files
├── processed/              # Processed images
├── samples/                # Sample PDFs for testing
├── handwritten_party/      # Handwritten documents output
└── output/                 # Main pipeline outputs
```

## Development

### Local Development
```bash
# Install dependencies
make install-deps

# Run locally
python -m jail-events.main --mode sample --step all
```

### Adding New Features
1. Modify the relevant module in `src/jail-events/`
2. Update tests in `tests/`
3. Test with sample data: `make sample-pipeline`
4. Build and test Docker: `make build && make sample-pipeline`

## Troubleshooting

### Common Issues

1. **Out of Memory**: Use sample or debug mode instead of full mode
2. **Docker Build Fails**: Ensure Docker has enough memory allocated
3. **OCR Errors**: Check that Tesseract is properly installed in the container
4. **Permission Errors**: Ensure Docker has access to the data directory

### Logs
- Processing logs are saved to `processing_logs_*.parquet`
- Check these files for detailed error information

## Performance

- **Full Pipeline**: ~2-4 hours (depending on hardware)
- **Sample Pipeline**: ~10-15 minutes
- **Debug Pipeline**: ~2-3 minutes
- **Handwritten Analysis**: ~5-15 minutes (depends on missing handwritten document count)

## Smart Handwritten Processing

The handwritten analysis uses intelligent processing based on existing person records:

1. **Reference Data**: Uses `jails_person_records.parquet` as the source of truth for processed pages
2. **Missing Detection**: Identifies handwritten pages (OCR < 80) that are missing from person records
3. **Selective Processing**: Only processes missing handwritten documents
4. **Same Fields**: Creates Excel with identical fields as main database
5. **Benefits**: 
   - Skips already processed pages
   - Only processes missing handwritten documents
   - Much faster than full pipeline
   - Same data quality as main database

### Data Flow
- `jails_person_records.parquet` (reference) + `jails_pdfs_full.parquet` (raw data)
- → Find handwritten pages missing from person records
- → Process only missing handwritten docs through cleaning pipeline
- → Excel export with image links

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with sample data
5. Submit a pull request
