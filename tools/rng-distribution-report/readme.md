# RNG Distribution Report

## Overview

Set of scripts used to generate RNG distribution report for certification purposes.

## Setup

### Prerequisites
- Python 3.9 or higher

### Installation
 
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

1. **Copy Data Extract**:

   Copy generated data extract csv file to the data_extract folder


2. **Generate JSON Report**:

   Run the following command to process input data and create a JSON report:
   ```bash
   python generate_json_report.py
   ```


3. **Generate Excel Report**:

   Run the following command to process input data and create an Excel report:
   ```bash
   python generate_excel_report.py
   ```