// src/components/SupplierOrdersModal.js

import React, { useState, useEffect } from "react";
import { Modal, Spin, message, List, Button, Typography, Card, Row, Col } from "antd";
import axios from "axios";
import dayjs from "dayjs";

const { Title, Text } = Typography;
const { Meta } = Card;

const SupplierOrdersModal = ({ visible, onClose, codice, ragioneSociale }) => {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [groupedOrders, setGroupedOrders] = useState({});
    const [selectedMonth, setSelectedMonth] = useState(null);

    useEffect(() => {
        if (visible) {
            fetchOrders();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [visible]);

    const fetchOrders = async () => {
        setLoading(true);
        try {
            const response = await axios.get("http://172.16.16.69:8000/supplier-orders", {
                params: {
                    codice: codice
                }
            });
            setOrders(response.data);
            groupOrdersByMonth(response.data);
        } catch (error) {
            message.error("Failed to fetch supplier orders.");
            console.error("Suppliers-order fetch error:", error);
        } finally {
            setLoading(false);
        }
    };

    // Group orders by month based on oft_data
    const groupOrdersByMonth = (ordersData) => {
        const groups = ordersData.reduce((acc, order) => {
            const month = dayjs(order.oft_data).format("MMMM YYYY"); // e.g., "Gennaio 2024"
            if (!acc[month]) {
                acc[month] = [];
            }
            acc[month].push(order);
            return acc;
        }, {});

        setGroupedOrders(groups);
    };

    // Handle month click
    const handleMonthClick = (month) => {
        setSelectedMonth(month);
    };

    // Handle back to months view
    const handleBack = () => {
        setSelectedMonth(null);
    };

    // Render the content based on whether a month is selected
    const renderContent = () => {
        if (loading) {
            return <Spin tip="Loading Orders..." />;
        }

        if (!orders.length) {
            return <Text>Nessun ordine trovato per questo fornitore.</Text>;
        }

        if (selectedMonth) {
            const ordersInMonth = groupedOrders[selectedMonth];
            return (
                <div>
                    <Button onClick={handleBack} style={{ marginBottom: 16 }}>
                        Indietro
                    </Button>
                    <Title level={4}>Ordini per {selectedMonth}</Title>
                    <List
                        itemLayout="horizontal"
                        dataSource={ordersInMonth}
                        renderItem={order => (
                            <List.Item>
                                <List.Item.Meta
                                    title={`Ordine ID: ${order.id}`} // Adjust according to your data structure
                                    description={`Data: ${dayjs(order.oft_data).format("DD-MM-YYYY")}, Dettagli: ${order.details}`} // Adjust fields as necessary
                                />
                            </List.Item>
                        )}
                    />
                </div>
            );
        }

        // Display grid of month cards
        return (
            <div>
                <Title level={4}>Ordini per {ragioneSociale}</Title>
                <Row gutter={[16, 16]}>
                    {Object.keys(groupedOrders).map((month) => (
                        <Col xs={24} sm={12} md={8} lg={6} key={month}>
                            <Card
                                hoverable
                                onClick={() => handleMonthClick(month)}
                                style={{ textAlign: 'center' }}
                            >
                                <Meta
                                    title={month}
                                    description={`${groupedOrders[month].length} Ordini`}
                                />
                            </Card>
                        </Col>
                    ))}
                </Row>
            </div>
        );
    };

    return (
        <Modal
            visible={visible}
            title={`Ordini Fornitore: ${ragioneSociale} (${codice})`}
            onCancel={onClose}
            footer={null}
            width={800}
        >
            {renderContent()}
        </Modal>
    );
};

export default SupplierOrdersModal;
