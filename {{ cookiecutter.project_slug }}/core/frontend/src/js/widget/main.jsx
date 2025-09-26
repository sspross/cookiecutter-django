import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Widget from './Widget.jsx'

createRoot(document.getElementById('widget')).render(
  <StrictMode>
    <Widget />
  </StrictMode>,
)
