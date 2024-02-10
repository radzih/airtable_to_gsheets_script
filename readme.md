# Airtable to Google Sheets script
This project is a Python script that pulls data from Airtable and pushes it to Google Sheets. It uses the httpx library to make HTTP requests to the Airtable API and fetches the data. The data is then processed and pushed to Google Sheets using the google-api-python-client library. The script uses ThreadPoolExecutor from the concurrent.futures module to perform multiple tasks concurrently, improving the efficiency of the script.  

## Setup
1. __Clone the repository__:
Use the command `git clone` to clone the repository to your local machine.
2. __Install the requirements__: The project uses Poetry for dependency management. 
If you don't have Poetry installed, you can install it by following the instructions on the official 
Poetry website. Once you have Poetry installed, navigate to the project directory in your terminal 
and run `poetry install` to install the project dependencies.  
3. __Set up the environment variables__: 
The script requires certain environment variables to be set. 
These include `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, and `GSHEET_SERVICE_ACCOUNT_CREDENTIALS`.
4. __Run the script__: 
Once the setup is complete, you can run the script using the command `python main.py`.
The script will fetch data from Airtable and push it to Google Sheets.

> Please note that you need to have Python 3.9 or higher installed on your machine to run this script.