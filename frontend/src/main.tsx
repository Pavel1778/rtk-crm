import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import { ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import dayjs from 'dayjs'
import 'dayjs/locale/ru'

// Настройка локали dayjs
dayjs.locale('ru')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={ruRU} theme={{
      token: {
        colorPrimary: '#0066CC', // Фирменный цвет Ростелекома
        borderRadius: 6,
      },
    }}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
