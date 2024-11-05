// src/components/RechartsBarChart.js

import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const RechartsBarChart = ({ data }) => {
    return (
        <ResponsiveContainer width="100%" height={300}>
            <BarChart
                data={data}
                margin={{
                    top: 20, right: 30, left: 20, bottom: 5,
                }}
            >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="dep_code" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="total_deposit" fill="#82ca9d" name="Total Orders" />
            </BarChart>
        </ResponsiveContainer>
    );
};

export default RechartsBarChart;
