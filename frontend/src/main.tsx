import React from 'react';
import {createRoot} from 'react-dom/client';
import {Theme} from '@astryxdesign/core/theme';
import {themes, defaultThemeSlug} from './astryx-themes';
import App from './App';
import './style.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Theme theme={themes[defaultThemeSlug]}><App /></Theme>
  </React.StrictMode>,
);
