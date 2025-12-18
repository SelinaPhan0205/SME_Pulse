// Metabase API service for React
// Handles login, query, and data fetch for cashflow_forecast & anomaly_result

import axios from 'axios';

const METABASE_URL = 'http://localhost:3000'; // Đổi thành URL Metabase của bạn nếu khác
const METABASE_USER = 'thanhsonnguyenvan22@gmail.com'; // Đổi thành user admin
const METABASE_PASS = 'NVTS220205s'; // Đổi thành password admin

let sessionToken: string | null = null;

// Login to Metabase, get session token
export async function loginMetabase() {
  if (sessionToken) return sessionToken;
  const res = await axios.post(`${METABASE_URL}/api/session`, {
    username: METABASE_USER,
    password: METABASE_PASS,
  });
  sessionToken = res.data.id;
  return sessionToken;
}

// Query Metabase table by native SQL
export async function queryMetabase(sql: string) {
  const token = await loginMetabase();
  const res = await axios.post(
    `${METABASE_URL}/api/dataset`,
    {
      database: 3, // Đã đổi thành DB id của bạn
      type: 'native',
      native: { query: sql },
    },
    {
      headers: { 'X-Metabase-Session': token },
    }
  );
  return res.data;
}

// Get cashflow forecast data
export async function getCashflowForecast() {
  return queryMetabase('SELECT * FROM cashflow_forecast');
}

// Get anomaly result data
export async function getAnomalyResult() {
  return queryMetabase('SELECT * FROM anomaly_result');
}
