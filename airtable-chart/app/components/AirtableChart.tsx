"use client";

import { useEffect, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

// Define the structure of each data item
interface DataItem {
  date: string;
  elapsedTime: number;
}

export default function AirtableChart() {
  // Use an explicit type for chartData to match the expected structure
  const [chartData, setChartData] = useState<{ labels: string[]; datasets: { label: string; data: number[]; backgroundColor: string }[] }>({ 
    labels: [], 
    datasets: [] 
  });

  useEffect(() => {
    fetch('/api/airtable-data')
      .then((response) => response.json())
      .then((data: DataItem[]) => {  // Specify data as an array of DataItem
        setChartData({
          labels: data.map((item) => item.date),
          datasets: [
            {
              label: 'Elapsed Time',
              data: data.map((item) => item.elapsedTime),
              backgroundColor: 'rgba(75, 192, 192, 0.6)',
            },
          ],
        });
      });
  }, []);

  return <Bar data={chartData} options={{ responsive: true, plugins: { legend: { position: 'top' } } }} />;
}
