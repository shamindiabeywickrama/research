export function weatherIcon(condition) {
  const key = (condition || '').toLowerCase()
  if (key.includes('thunder')) return '⛈'
  if (key.includes('heavy rain')) return '🌧'
  if (key.includes('rain') || key.includes('drizzle')) return '🌦'
  if (key.includes('snow')) return '❄'
  if (key.includes('fog')) return '🌫'
  if (key.includes('cloud')) return '☁'
  if (key.includes('clear')) return '☀'
  return '🌤'
}

export function isWifiMode(dataMode) {
  return dataMode === 'wifi' || dataMode === 'wifi_weather'
}
