// src/components/Notifications.js
import React from 'react';
import { Alert } from 'antd';

function Notifications({ inventoryData }) {
  const understockItems = inventoryData.filter(item => item.understock_alert);

  if (understockItems.length === 0) return null;

  return (
    <Alert
      message="Understock Alerts"
      description={
        <ul>
          {understockItems.map(item => (
            <li key={item.item_code}>
              {item.item_code} - {item.description} is below minimum stock!
            </li>
          ))}
        </ul>
      }
      type="warning"
      showIcon
    />
  );
}

export default Notifications;
