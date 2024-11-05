import React, { useEffect, useState } from "react";
import { Table, Button, Spin } from "antd";
import axios from "axios";
import { Link } from "react-router-dom";

const App = () => {
  const [reportData, setReportData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    axios.get("http://localhost:5000/report")
      .then(response => {
        const data = response.data;
        setReportData(data);

        // Generate notifications for understocked items
        const underStock = data.filter(item => {
          return item.giac_d01 < item.scrt || (item.ord_mp && item.ord_mp > item.giac_d01);
        });

        // Store notifications in localStorage
        const notifications = underStock.map(item => ({
          id: item.c_articolo,  // Unique identifier
          message: `${item.c_articolo} - ${item.d_articolo} is under minimum stock or needed soon!`,
          date: new Date().toLocaleString(),
        }));
        
        localStorage.setItem('mrpNotifications', JSON.stringify(notifications));  // Store in localStorage
        setLoading(false);
      })
      .catch(error => {
        console.error("Error fetching report:", error);
        setLoading(false);
      });
  }, []);

  const columns = [
    {
      title: "Item Code",
      dataIndex: "c_articolo",
      key: "c_articolo",
    },
    {
      title: "Description",
      dataIndex: "d_articolo",
      key: "d_articolo",
    },
    {
      title: "Type",
      dataIndex: "a_p",
      key: "a_p",
    },
    {
      title: "Lead Time",
      dataIndex: "lt",
      key: "lt",
    },
    {
      title: "Min Stock",
      dataIndex: "scrt",
      key: "scrt",
    },
    {
      title: "Depot 01 Stock",
      dataIndex: "giac_d01",
      key: "giac_d01",
    },
    {
      title: "Available Stock (Depot 01)",
      dataIndex: "disp_d01",
      key: "disp_d01",
    },
    {
      title: "Future Order (MP)",
      dataIndex: "ord_mp",
      key: "ord_mp",
    },
  ];

  return (
    <div style={{ padding: 20 }}>
      <h1>MRP Report</h1>
      <Button type="primary">
        <Link to="/understock">Items Under Minimum Stock</Link>
      </Button>

      <Spin spinning={loading} tip="Loading...">
        <Table columns={columns} dataSource={reportData} rowKey="c_articolo" />
      </Spin>
    </div>
  );
};

export default App;
