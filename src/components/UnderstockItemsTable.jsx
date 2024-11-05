// src/components/UnderstockItemsTable.js

import React from "react";
import { Table } from "antd";

const UnderstockItemsTable = ({ data }) => {
    const columns = [
        {
            title: 'Item Code',
            dataIndex: 'item_code',
            key: 'item_code',
            sorter: (a, b) => a.item_code.localeCompare(b.item_code),
        },
        {
            title: 'Item Description',
            dataIndex: 'item_description',
            key: 'item_description',
            sorter: (a, b) => a.item_description.localeCompare(b.item_description),
        },
        {
            title: 'Current Stock',
            dataIndex: 'current_stock',
            key: 'current_stock',
            sorter: (a, b) => a.current_stock - b.current_stock,
        },
        {
            title: 'Minimum Required',
            dataIndex: 'min_required',
            key: 'min_required',
            sorter: (a, b) => a.min_required - b.min_required,
        },
        {
            title: 'Reorder Quantity',
            dataIndex: 'reorder_qty',
            key: 'reorder_qty',
            sorter: (a, b) => a.reorder_qty - b.reorder_qty,
        },
    ];

    return (
        <Table
        
            columns={columns}
            dataSource={data}
            rowKey="item_code"
            
            pagination={{ pageSize: 5 }}
        />
    );
};

export default UnderstockItemsTable;
