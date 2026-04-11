
import React from 'react';
import ReactDOMServer from 'react-dom/server';
import Page from './[id].tsx';
import Layout0 from '../../layout.tsx';
import Layout1 from '../layout.tsx';


const params = JSON.parse(process.argv[2] || "{}");

const html = ReactDOMServer.renderToString(
    
React.createElement(
    Layout1,
    null,
    
React.createElement(
    Layout0,
    null,
    React.createElement(Page, { params })
)
    
)
    
);

console.log(html);
    