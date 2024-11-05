import React, { useState, useEffect } from "react";
import { Table, Tag, notification } from "antd";
import axios from "axios";

const Inventory = () => {
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get("http://localhost:5000/inventory")
      .then(response => {
        setInventory(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error("Error fetching inventory", error);
        notification.error({
          message: "Error",
          description: "Failed to fetch inventory data."
        });
      });
  }, []);

  const columns = [
    {
      title: "Item Code",
      dataIndex: "item_code",
      key: "item_code",
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
    },
    {
      title: "Lead Time",
      dataIndex: "lead_time",
      key: "lead_time",
    },
    {
      title: "Total Stock",
      dataIndex: "total_stock",
      key: "total_stock",
    },
    {
      title: "Min Stock",
      dataIndex: "min_stock",
      key: "min_stock",
    },
    {
      title: "Understock Alert",
      dataIndex: "understock_alert",
      key: "understock_alert",
      render: (alert) => (
        <Tag color={alert ? "red" : "green"}>
          {alert ? "Understocked" : "Stock OK"}
        </Tag>
      ),
    },
  ];

  return (
    <div>
      <h1>Inventory Overview</h1>
      <Table dataSource={inventory} columns={columns} rowKey="item_code" loading={loading} />
    </div>
  );
};

export default Inventory;
