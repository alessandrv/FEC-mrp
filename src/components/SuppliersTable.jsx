// src/components/SuppliersTable.js

// src/components/SuppliersTable.js

import React, { useState, useEffect } from "react";
import { Table, Spin, message, Input, Button } from "antd";
import axios from "axios";
import SupplierOrdersModal from "./SupplierOrdersModal"; // Import the modal component
import { SearchOutlined } from '@ant-design/icons'; // Optional: Add search icon
const { Search } = Input;

const SuppliersTable = ({ dateRange }) => {
    const [suppliers, setSuppliers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [selectedSupplier, setSelectedSupplier] = useState(null);

    // Define table columns
    const columns = [
        {
            title: 'Codice',
            dataIndex: 'cod_clifor',
            key: 'cod_clifor',
            sorter: (a, b) => a.cod_clifor.localeCompare(b.cod_clifor),
        },
        {
            title: 'Ragione Sociale',
            dataIndex: 'des_clifor',
            key: 'des_clifor',
            sorter: (a, b) => a.des_clifor.localeCompare(b.des_clifor),
        },
        {
            title: 'Azioni',
            key: 'azioni',
            render: (text, record) => (
                <Button
                    type="primary"
                    onClick={() => handleSelectSupplier(record)}
                >
                    Seleziona
                </Button>
            ),
        },
    ];

    useEffect(() => {
        const fetchSuppliers = async () => {
            setLoading(true);
            try {
                const response = await axios.get("http://172.16.16.69:8000/suppliers", {
                    params: {
                        start_date: dateRange[0].format('DD-MM-YYYY'),
                        end_date: dateRange[1].format('DD-MM-YYYY')
                    }
                });
                setSuppliers(response.data);
            } catch (error) {
                message.error("Failed to fetch suppliers.");
                console.error("Suppliers fetch error:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchSuppliers();
    }, [dateRange]);

    // Handle search input changes
    const handleSearch = (value) => {
        setSearchTerm(value);
    };

    // Handle "Seleziona" button click
    const handleSelectSupplier = (supplier) => {
        setSelectedSupplier(supplier);
        setIsModalVisible(true);
    };

    // Handle modal close
    const handleModalClose = () => {
        setIsModalVisible(false);
        setSelectedSupplier(null);
    };

    // Filter suppliers based on search term
    const filteredSuppliers = suppliers.filter(supplier => 
        supplier.cod_clifor.toLowerCase().includes(searchTerm.toLowerCase()) ||
        supplier.des_clifor.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (loading) {
        return <Spin tip="Loading Suppliers..." />;
    }

    return (
        <div>
            {/* Search Bar */}
            <Search
                placeholder="Cerca per Codice o Ragione Sociale"
                allowClear
                enterButton={<SearchOutlined />}
                size="middle"
                onSearch={handleSearch}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ marginBottom: 16, width: 300 }}
            />
            
            {/* Suppliers Table */}
            <Table
                columns={columns}
                dataSource={filteredSuppliers}
                rowKey="cod_clifor"
                pagination={{ pageSize: 20 }}
                bordered
            />

            {/* Supplier Orders Modal */}
            {selectedSupplier && (
                <SupplierOrdersModal
                    visible={isModalVisible}
                    onClose={handleModalClose}
                    codice={selectedSupplier.cod_clifor}
                    ragioneSociale={selectedSupplier.des_clifor}
                />
            )}
        </div>
    );
};

export default SuppliersTable;
