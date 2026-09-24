import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import Polar3DAtmosphere from './Polar3DAtmosphere'
import './styles.css'
import './digital-twin.css'
import './interactions.css'
import './system-interaction.css'

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><Polar3DAtmosphere /><App /></React.StrictMode>)
