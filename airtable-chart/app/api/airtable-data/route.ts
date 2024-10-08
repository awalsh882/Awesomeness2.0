import { NextResponse } from 'next/server';

interface AirtableRecord {
  id: string;
  fields: {
    Date?: string;
    Activity?: string;
    'Elapsed Time'?: number;
  };
}

export async function GET() {
  const baseId = process.env.AIRTABLE_BASE_ID;
  const tableName = process.env.AIRTABLE_TABLE_NAME;
  const url = `https://api.airtable.com/v0/${baseId}/${tableName}`;
  const apiKey = process.env.AIRTABLE_API_KEY;

  try {
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Error: ${response.statusText}, Details: ${errorText}`);
    }

    const data: { records: AirtableRecord[] } = await response.json();

    // Ensure proper extraction and formatting
    const formattedData = data.records.map((record) => ({
      date: record.fields.Date || 'No Date',        
      activity: record.fields.Activity || 'No Activity',
      elapsedTime: record.fields['Elapsed Time'] || 0,
    }));

    return NextResponse.json(formattedData);
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: 'Failed to fetch data from Airtable' }, { status: 500 });
  }
}
