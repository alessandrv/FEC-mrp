import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Space, message, Card, Tooltip } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined, DragOutlined, SearchOutlined } from '@ant-design/icons';
import { DndContext, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import axios from 'axios';
import './ProductsAvailability.css';

const ProductsAvailability = () => {
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

  // Fetch data from API
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await axios.get('http://172.16.16.27:8000/get_disponibilita_articoli');
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
      const response = await axios.put('http://172.16.16.27:8000/update_disponibilita_articoli_order', [itemA, itemB]);
      
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
      const response = await axios.get(`http://172.16.16.27:8000/get_article_description/${code}`);
      
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
          await axios.put('http://172.16.16.27:8000/update_disponibilita_articolo', values);
          
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
          await axios.post('http://172.16.16.27:8000/add_disponibilita_articolo', values);
          
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
        await axios.delete(`http://172.16.16.27:8000/delete_disponibilita_articolo/${selectedRowForDelete.posizione}`);
        
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

  // Move row up - Updated to use the new swap positions approach
  const moveRowUp = (record) => {
    if (record.posizione === 1) return; // Already at the top
    
    const currentIndex = dataSource.findIndex(item => item.posizione === record.posizione);
    if (currentIndex <= 0) return;
    
    const prevItem = dataSource[currentIndex - 1];
    
    message.loading('Spostamento in alto...', 0.5);
    // Send the two items to swap to the backend
    saveData(record, prevItem)
      .then(success => {
        if (!success) {
          // If the save failed, refresh the data to ensure UI is in sync with backend
          setTimeout(() => fetchData(), 1000);
        }
      });
  };
  
  // Move row down - Updated to use the new swap positions approach
  const moveRowDown = (record) => {
    if (record.posizione === dataSource.length) return; // Already at the bottom
    
    const currentIndex = dataSource.findIndex(item => item.posizione === record.posizione);
    if (currentIndex >= dataSource.length - 1) return;
    
    const nextItem = dataSource[currentIndex + 1];
    
    message.loading('Spostamento in basso...', 0.5);
    // Send the two items to swap to the backend
    saveData(record, nextItem)
      .then(success => {
        if (!success) {
          // If the save failed, refresh the data to ensure UI is in sync with backend
          setTimeout(() => fetchData(), 1000);
        }
      });
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

  return (
    <div className="products-availability-container">
      <Card 
        title="Disponibilità Articoli" 
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

export default ProductsAvailability;
