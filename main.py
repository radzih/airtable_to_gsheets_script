import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import httpx
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

AIRTABLE_API_KEY = ""
AIRTABLE_BASE_ID = ""

GSHEET_SERVICE_ACCOUNT_CREDENTIALS = {}


@dataclass
class Record:
    values: list[str]


@dataclass
class Table:
    airtable_id: str
    name: str
    columns: list[str]
    records: list[Record]


def configure_logging(debug: bool = False):
    level = logging.DEBUG if debug else logging.INFO
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)
    logging.basicConfig(level=level, format="%(levelname)-8s %(asctime)s: %(message)s")


def copy_airtable_tables(base_id: str) -> list[Table]:
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    response = httpx.get(f"https://api.airtable.com/v0/meta/bases/{base_id}/tables", headers=headers)

    if response.is_error:
        logging.error(f"Failed to fetch tables: {response.text}")
        exit(1)

    response_data = response.json()
    tables = []

    for data in response_data["tables"]:
        table = Table(
            airtable_id=data["id"],
            name=data["name"],
            columns=[field["name"] for field in data["fields"]],
            records=[],
        )
        tables.append(table)

    with ThreadPoolExecutor() as executor:
        executor.map(copy_records_to_table, tables)

    return tables


def copy_records_to_table(table: Table):
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    offset = None
    records = []

    while True:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table.airtable_id}"
        response = httpx.get(url, headers=headers, params={"offset": offset})

        if response.is_error:
            logging.error(f"Failed to fetch table {table.name}: {response.text}")
            exit(1)

        response_data = response.json()

        for record in response_data["records"]:
            records.append(
                Record(
                    values=[record["fields"].get(column) for column in table.columns]
                )
            )

        offset = response_data.get("offset")
        if not offset:
            break

    table.records = records


def create_google_spreadsheet(tables: list[Table]) -> str:
    credentials = Credentials.from_service_account_info(
        GSHEET_SERVICE_ACCOUNT_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )

    service = build('sheets', 'v4', credentials=credentials)
    drive_service = build('drive', 'v3', credentials=credentials)
    spreadsheet_body = {
        'properties': {'title': 'My Spreadsheet'},
        'sheets': [{'properties': {'title': table.name}} for table in tables]
    }

    request = service.spreadsheets().create(body=spreadsheet_body)
    response = request.execute()

    spreadsheet_id = response['spreadsheetId']

    drive_service.permissions().create(
        fileId=spreadsheet_id,
        body={
            'type': 'anyone',
            'role': 'writer',
        },
        fields='id',
    ).execute()

    return spreadsheet_id


def fill_gsheet_table(table: Table, spreadsheet_id: str):
    logging.info(f"Filling table {table.name}")

    credentials = Credentials.from_service_account_info(
        GSHEET_SERVICE_ACCOUNT_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )

    service = build('sheets', 'v4', credentials=credentials)

    column_values = [table.columns]

    column_range_name = f'{table.name}!A1:{chr(65 + len(table.columns))}1'
    column_body = {
        'range': column_range_name,
        'values': column_values
    }

    query = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=column_range_name,
        valueInputOption='RAW', body=column_body
    )
    query.execute()

    body = {
        "data": [
            {
                "range": f"{table.name}!A2:{chr(65 + len(table.columns))}{len(table.records) + 2}",
                "majorDimension": "ROWS",
                "values": [record.values for record in table.records],
            }
        ],
        "valueInputOption": 'RAW',
    }

    query = service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body,
    )
    query.execute()


def fill_gsheet_tables(tables: list[Table], spreadsheet_id: str):
    with ThreadPoolExecutor() as executor:
        executor.map(lambda table: fill_gsheet_table(table, spreadsheet_id), tables)


def main():
    configure_logging()
    logging.info("Starting the application")

    logging.info("Copying Airtable tables")
    tables = copy_airtable_tables(AIRTABLE_BASE_ID)
    logging.info(f"Creating {len(tables)} tables in Google Sheets")

    spreadsheet_id = create_google_spreadsheet(tables)
    logging.info(f"Spreadsheet created with ID {spreadsheet_id}")

    fill_gsheet_tables(tables, spreadsheet_id)

    logging.info("All tables have been created")

    logging.info("Spreadsheet url: https://docs.google.com/spreadsheets/d/" + spreadsheet_id)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Exiting the application")
