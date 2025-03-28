import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Space, message, Card, Tooltip, Tabs } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined, DragOutlined, SearchOutlined } from '@ant-design/icons';
import { DndContext, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import axios from 'axios';
import './ProductsAvailability.css';
import { API_BASE_URL } from './config'; // Import configuration

const ProductsAvailabilityTabs = () => {
  // State for active tab
  const [activeTab, setActiveTab] = useState('1');
  
  // State for products data
  const [dataSource, setDataSource] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingDescription, setLoadingDescription] = useState(false);
  
  // State for modal visibility and form
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isDeleteModalVisible, setIsDeleteModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [selectedRowForDelete, setSelectedRowForDelete] = useState(null);
  
  // Form reference
  const [form] = Form.useForm();
  
  // For drag-and-drop functionality
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 1,
      },
    })
  );

  // Fetch data based on active tab
  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const endpoint = activeTab === '1' 
        ? `${API_BASE_URL}/get_disponibilita_articoli`
        : `${API_BASE_URL}/get_disponibilita_articoli_commerciali`;
      
      const response = await axios.get(endpoint);
      setDataSource(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      message.error('Errore durante il caricamento dei dati');
      setLoading(false);
      setDataSource([]);  // Initialize with empty array on error
    }
  };

  // Save changes to API - Updated to use the new swap positions approach
  const saveData = async (itemA, itemB) => {
    try {
      // Send only the two items to swap positions
      const endpoint = activeTab === '1'
        ? `${API_BASE_URL}/update_disponibilita_articoli_order`
        : `${API_BASE_URL}/update_disponibilita_articoli_order_commerciali`;
      
      const response = await axios.put(endpoint, [itemA, itemB]);
      
      // Fetch the updated data to ensure UI is in sync with backend
      fetchData();
      
      message.success(`Posizioni scambiate: ${itemA.posizione} ↔ ${itemB.posizione}`);
      return true;
    } catch (error) {
      console.error('Error saving data:', error);
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        message.error(`Errore ${error.response.status}: ${error.response.data.message || 'Errore durante il salvataggio dei dati'}`);
      } else if (error.request) {
        // The request was made but no response was received
        message.error('Nessuna risposta dal server. Controlla la connessione.');
      } else {
        // Something happened in setting up the request that triggered an Error
        message.error('Errore durante il salvataggio dei dati');
      }
      return false;
    }
  };

  // Modal handlers
  const showModal = (record = null) => {
    setEditingRecord(record);
    form.resetFields();
    
    if (record) {
      // For editing existing record
      form.setFieldsValue({
        posizione: record.posizione,
        codice: record.codice,
        descrizione: record.descrizione,
      });
    } else {
      // For new record, set default position as last+1
      const nextPosition = dataSource.length > 0 
        ? Math.max(...dataSource.map(item => item.posizione)) + 1 
        : 1;
      form.setFieldsValue({
        posizione: nextPosition,
        codice: '',
        descrizione: '',
      });
    }
    
    setIsModalVisible(true);
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    setIsDeleteModalVisible(false);
  };

  // Function to fetch description based on code
  const fetchDescription = async () => {
    let code = form.getFieldValue('codice');
    if (!code) {
      message.warning('Inserisci un codice prima di cercare la descrizione');
      return;
    }

    // If there are multiple codes separated by commas, use only the first one
    if (code.includes(',')) {
      code = code.split(',')[0].trim();
      message.info(`Utilizzando il primo codice: ${code}`);
    }

    setLoadingDescription(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/get_article_description/${code}`);
      
      if (response.data && response.data.description) {
        form.setFieldsValue({
          descrizione: response.data.description
        });
        message.success('Descrizione trovata e applicata');
      } else {
        message.warning('Nessuna descrizione trovata per questo codice');
      }
    } catch (error) {
      console.error('Error fetching description:', error);
      if (error.response && error.response.status === 404) {
        message.warning(`Nessuna descrizione trovata per il codice: ${code}`);
      } else {
        message.error('Errore durante il recupero della descrizione');
      }
    } finally {
      setLoadingDescription(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      let newData = [...dataSource];
      
      if (editingRecord) {
        // Update existing record via API
        try {
          const endpoint = activeTab === '1'
            ? `${API_BASE_URL}/update_disponibilita_articolo`
            : `${API_BASE_URL}/update_disponibilita_articolo_commerciali`;
          
          await axios.put(endpoint, values);
          
          // Update local state
          newData = newData.map(item => 
            item.posizione === editingRecord.posizione ? { ...item, ...values } : item
          );
          
          message.success('Articolo aggiornato con successo');
        } catch (error) {
          console.error('Error updating record:', error);
          message.error('Errore durante l\'aggiornamento dell\'articolo');
          return; // Exit early if update fails
        }
      } else {
        // Add new record via API
        try {
          const endpoint = activeTab === '1'
            ? `${API_BASE_URL}/add_disponibilita_articolo`
            : `${API_BASE_URL}/add_disponibilita_articolo_commerciali`;
          
          await axios.post(endpoint, values);
          
          // Add to local state
          newData.push(values);
          message.success('Articolo aggiunto con successo');
        } catch (error) {
          console.error('Error adding record:', error);
          message.error('Errore durante l\'aggiunta dell\'articolo');
          return; // Exit early if add fails
        }
      }
      
      // Sort by position
      newData.sort((a, b) => a.posizione - b.posizione);
      
      setDataSource(newData);
      setIsModalVisible(false);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  // Delete handlers
  const showDeleteModal = (record) => {
    setSelectedRowForDelete(record);
    setIsDeleteModalVisible(true);
  };

  const handleDelete = async () => {
    if (selectedRowForDelete) {
      try {
        // Delete record via API
        const endpoint = activeTab === '1'
          ? `${API_BASE_URL}/delete_disponibilita_articolo/${selectedRowForDelete.posizione}`
          : `${API_BASE_URL}/delete_disponibilita_articolo_commerciali/${selectedRowForDelete.posizione}`;
        
        await axios.delete(endpoint);
        
        // Update local state
        const newData = dataSource.filter(
          item => item.posizione !== selectedRowForDelete.posizione
        );
        
        // No need to renumber positions here as the backend handles it
        
        setDataSource(newData);
        setIsDeleteModalVisible(false);
        message.success('Articolo eliminato con successo');
      } catch (error) {
        console.error('Error deleting record:', error);
        message.error('Errore durante l\'eliminazione dell\'articolo');
      }
    }
  };

  // Handle tab change
  const handleTabChange = (key) => {
    setActiveTab(key);
  };

  // Update the onDragEnd function to use the new swap approach
  const onDragEnd = ({ active, over }) => {
    if (active.id !== over.id) {
      const activeItem = dataSource.find(item => item.posizione === active.id);
      const overItem = dataSource.find(item => item.posizione === over.id);
      
      if (activeItem && overItem) {
        message.loading('Aggiornamento posizioni...', 0.5);
        // Send the two items to swap to the backend
        saveData(activeItem, overItem)
          .then(success => {
            if (!success) {
              // If the save failed, refresh the data to ensure UI is in sync with backend
              setTimeout(() => fetchData(), 1000);
            }
          });
      }
    }
  };

  // Define the drag handle component
  const DragHandle = ({ nodeRef, ...props }) => {
    const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
      id: props.id,
    });
    
    const style = {
      transform: CSS.Transform.toString(transform),
      transition,
      cursor: 'move',
      touchAction: 'none',
    };
    
    return (
      <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
        <DragOutlined />
      </div>
    );
  };

  // Table row component with drag and drop capabilities
  const Row = ({ children, ...props }) => {
    const {
      attributes,
      listeners,
      setNodeRef,
      transform,
      transition,
      isDragging,
    } = useSortable({
      id: props['data-row-key'],
    });
    
    const style = {
      ...props.style,
      transform: CSS.Transform.toString(transform),
      transition,
      opacity: isDragging ? 0.5 : 1,
    };
    
    return (
      <tr
        {...props}
        ref={setNodeRef}
        style={style}
        {...attributes}
      >
        {children}
      </tr>
    );
  };

  // Table columns definition
  const columns = [
    {
      title: '',
      dataIndex: 'sort',
      width: 50,
      render: (_, record) => (
        <DragHandle id={record.posizione} />
      ),
    },
    {
      title: 'Posizione',
      dataIndex: 'posizione',
      key: 'posizione',
      width: 100,
      sorter: (a, b) => a.posizione - b.posizione,
    },
    {
      title: 'Codice',
      dataIndex: 'codice',
      key: 'codice',
      render: (codice) => {
        // Split multiple codes if present
        if (codice && codice.includes(',')) {
          const codes = codice.split(',');
          return (
            <>
              {codes.map((code, index) => (
                <div key={index}>{code.trim()}</div>
              ))}
            </>
          );
        }
        return codice;
      },
    },
    {
      title: 'Descrizione',
      dataIndex: 'descrizione',
      key: 'descrizione',
    },
    {
      title: 'Azioni',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="Modifica">
            <Button 
              icon={<EditOutlined />} 
              onClick={() => showModal(record)}
              type="primary"
              ghost
            />
          </Tooltip>
          <Tooltip title="Elimina">
            <Button 
              icon={<DeleteOutlined />} 
              onClick={() => showDeleteModal(record)} 
              danger
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const getTabTitle = () => {
    return activeTab === '1' ? 'Disponibilità HUB' : 'Disponibilità Commerciali';
  };

  return (
    <div className="products-availability-container">
      <Card
        title={getTabTitle()}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => showModal()}
          >
            Aggiungi
          </Button>
        }
      >
        <Tabs activeKey={activeTab} onChange={handleTabChange} size="large">
          <Tabs.TabPane tab="Disponibilità HUB" key="1">
            <DndContext
              sensors={sensors}
              modifiers={[restrictToVerticalAxis]}
              onDragEnd={onDragEnd}
            >
              <SortableContext
                items={dataSource.map(item => item.posizione)}
                strategy={verticalListSortingStrategy}
              >
                <Table
                  components={{
                    body: {
                      row: Row,
                    },
                  }}
                  rowKey="posizione"
                  columns={columns}
                  dataSource={dataSource}
                  loading={loading}
                  pagination={false}
                  bordered
                />
              </SortableContext>
            </DndContext>
          </Tabs.TabPane>
          <Tabs.TabPane tab="Disponibilità Commerciali" key="2">
            <DndContext
              sensors={sensors}
              modifiers={[restrictToVerticalAxis]}
              onDragEnd={onDragEnd}
            >
              <SortableContext
                items={dataSource.map(item => item.posizione)}
                strategy={verticalListSortingStrategy}
              >
                <Table
                  components={{
                    body: {
                      row: Row,
                    },
                  }}
                  rowKey="posizione"
                  columns={columns}
                  dataSource={dataSource}
                  loading={loading}
                  pagination={false}
                  bordered
                />
              </SortableContext>
            </DndContext>
          </Tabs.TabPane>
        </Tabs>
      
        {/* Add/Edit Modal */}
        <Modal
          title={editingRecord ? "Modifica Articolo" : "Aggiungi Articolo"}
          open={isModalVisible}
          onOk={handleSubmit}
          onCancel={handleCancel}
          destroyOnClose
        >
          <Form
            form={form}
            layout="vertical"
            name="productForm"
          >
            <Form.Item
              name="posizione"
              label="Posizione"
              rules={[{ required: true, message: 'Inserisci la posizione' }]}
            >
              <Input type="number" min={1} />
            </Form.Item>
            
            <Form.Item
              name="codice"
              label="Codice"
              rules={[{ required: true, message: 'Inserisci il codice' }]}
              tooltip="Per inserire codici multipli, separali con una virgola"
            >
              <Input />
            </Form.Item>
            
            <Form.Item
              name="descrizione"
              label="Descrizione"
              rules={[{ required: true, message: 'Inserisci la descrizione' }]}
            >
              <Input addonAfter={
                <Button 
                  size="small" 
                  onClick={fetchDescription} 
                  title="Cerca descrizione dal codice"
                  icon={<SearchOutlined />}
                  loading={loadingDescription}
                  disabled={loadingDescription}
                >
                  Cerca
                </Button>
              } />
            </Form.Item>
          </Form>
        </Modal>
        
        {/* Delete Confirmation Modal */}
        <Modal
          title="Conferma Eliminazione"
          open={isDeleteModalVisible}
          onOk={handleDelete}
          onCancel={handleCancel}
          okText="Elimina"
          cancelText="Annulla"
          okButtonProps={{ danger: true }}
        >
          <p>Sei sicuro di voler eliminare questo articolo?</p>
          {selectedRowForDelete && (
            <p>
              <strong>Codice:</strong> {selectedRowForDelete.codice}<br />
              <strong>Descrizione:</strong> {selectedRowForDelete.descrizione}
            </p>
          )}
        </Modal>
      </Card>
    </div>
  );
};

export default ProductsAvailabilityTabs; 