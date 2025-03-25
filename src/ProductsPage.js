import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Container,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  TextField,
  Button,
  Card,
  CardContent,
  CardActions,
  InputAdornment,
  IconButton,
  Alert,
  Menu,
  MenuItem,
  Modal,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { styled } from '@mui/material/styles';
import axios from 'axios';
import { Visibility, VisibilityOff, MoreVert } from '@mui/icons-material'; // Import icons for password field

// Styled components for the table
const StyledTableContainer = styled(TableContainer)(({ theme }) => ({
  marginBottom: '2rem',
  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  borderRadius: '8px',
  overflow: 'hidden'
}));

const StyledTable = styled(Table)(({ theme }) => ({
  minWidth: 650,
}));

const TableHeaderCell = styled(TableCell)(({ theme }) => ({
  backgroundColor: '#2b2b2b',
  color: 'white',
  fontWeight: 'bold',
  textAlign: 'center',
  padding: '16px',
}));

const ProductNameCell = styled(TableCell)(({ theme }) => ({
  fontWeight: 'bold',
  color: '#2b2b2b',
  padding: '16px',
  width: '30%',
}));

const AvailabilityCell = styled(TableCell)(({ theme }) => ({
  textAlign: 'center',
  padding: '16px',
}));

// Create a styled cell for the code column
const CodeCell = styled(TableCell)(({ theme }) => ({
  fontFamily: 'monospace',
  padding: '16px',
  width: '15%',
}));

// Create a styled cell for the action button
const ActionCell = styled(TableCell)(({ theme }) => ({
  padding: '8px',
  width: '60px',
}));

// Create styled components for the login form
const LoginCard = styled(Card)(({ theme }) => ({
  maxWidth: 400,
  margin: '0 auto',
  marginTop: theme.spacing(8),
  padding: theme.spacing(3),
  boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
  borderRadius: '8px',
}));

const LoginButton = styled(Button)(({ theme }) => ({
  marginTop: theme.spacing(2),
  backgroundColor: '#2b2b2b',
  '&:hover': {
    backgroundColor: '#444444',
  },
}));

// Function to check if a component is a CPU
const isCpuComponent = (name) => {
  return /i[3579]|cpu|processor|intel|amd|ryzen/i.test(name);
};

// Function to format product and dependency names with styled CPU components
const formatProductName = (productName, dependencyName = null) => {
  if (!dependencyName) {
    // For products without dependencies
    
    return productName;
  }
  
  // For products with dependencies
  if (isCpuComponent(dependencyName)) {
    return (
      <>
        {productName}
      </>
    );
  }
  
  return `${productName} with ${dependencyName}`;
};

// Get current month name
const getCurrentMonthName = () => {
  return new Date().toLocaleString('en-US', { month: 'long' });
};

// Get next month name
const getNextMonthName = () => {
  const date = new Date();
  date.setMonth(date.getMonth() + 1);
  return date.toLocaleString('en-US', { month: 'long' });
};

// Get month name for 2 months ahead
const getNextPlusTwoMonthName = () => {
  const date = new Date();
  date.setMonth(date.getMonth() + 2);
  return date.toLocaleString('en-US', { month: 'long' });
};

// Get month name for 3 months ahead
const getNextPlusThreeMonthName = () => {
  const date = new Date();
  date.setMonth(date.getMonth() + 3);
  return date.toLocaleString('en-US', { month: 'long' });
};

// Function to calculate availability based on the period with recursive logic
const calculateAvailability = (record, month) => {
  if (!record) return 0;
  
  // With the new API format, record is the direct item object, not an array
  const data = record;
  
  const giacD01 = data.giac_d01 || 0;

  if (month === "today") {
    return giacD01;
  } else if (month === "mc") {
    // First month (m corr.)
    const domMc = data.dom_mc || 0;
    const offMc = data.off_mc || 0;
    const result = giacD01 - domMc + offMc;
    return result;
  } else if (month === "ms") {
    // Next month (m succ.)
    const currentMonthAvailability = calculateAvailability(record, "mc");
    const domMs = data.dom_ms || 0;
    const offMs = data.off_ms || 0;
    const result = currentMonthAvailability - domMs + offMs;
    return result;
  } else if (month === "msa") {
    // Following month (2m succ.)
    const nextMonthAvailability = calculateAvailability(record, "ms");
    const domMsa = data.dom_msa || 0;
    const offMsa = data.off_msa || 0;
    const result = nextMonthAvailability - domMsa + offMsa;
    return result;
  } else if (month === "mss") {
    // Third successive month (3m+ succ.)
    const secondMonthAvailability = calculateAvailability(record, "msa");
    const domMss = data.dom_mss || 0;
    const offMss = data.off_mss || 0;
    const result = secondMonthAvailability - domMss + offMss;
    return result;
  }
  
  return 0; // default for undefined month parameter
};

// Function to ensure negative values are displayed as zero
const displayValue = (value) => {
  return value < 0 ? 0 : value;
};

const ProductsPage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // State for context menu
  const [menuAnchorEl, setMenuAnchorEl] = useState(null);
  const [selectedProductId, setSelectedProductId] = useState(null);
  
  // Authentication states
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('FECItalia2025');
  const [username, setUsername] = useState('admin'); // Default username
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [authToken, setAuthToken] = useState('');
  
  const currentMonth = getCurrentMonthName().charAt(0).toUpperCase() + getCurrentMonthName().slice(1);
  const nextMonth = getNextMonthName().charAt(0).toUpperCase() + getNextMonthName().slice(1);
  const nextPlusTwoMonths = getNextPlusTwoMonthName().charAt(0).toUpperCase() + getNextPlusTwoMonthName().slice(1);
  const nextPlusThreeMonths = getNextPlusThreeMonthName().charAt(0).toUpperCase() + getNextPlusThreeMonthName().slice(1) + "+";

  // Add state variables for order history modal
  const [isOrderHistoryModalVisible, setIsOrderHistoryModalVisible] = useState(false);
  const [orderHistoryData, setOrderHistoryData] = useState([]);
  const [orderHistoryLoading, setOrderHistoryLoading] = useState(false);
  const [orderHistoryModalTitle, setOrderHistoryModalTitle] = useState("");

  // Context menu handlers
  const handleMenuOpen = (event, productId) => {
    setMenuAnchorEl(event.currentTarget);
    setSelectedProductId(productId);
  };

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
    setSelectedProductId(null);
  };
  
  // Menu item actions
  const handleViewDetails = () => {
    const product = products.find(p => p.id === selectedProductId);
    console.log('View details for product:', product);
    handleMenuClose();
    // Add your details view logic here
  };

  const handleExportProduct = () => {
    const product = products.find(p => p.id === selectedProductId);
    console.log('Export product:', product);
    handleMenuClose();
    // Add your export logic here
  };

  // Add handler for Impegno corrente (Current Commitment)
  const handleStoricoOrdini = () => {
    const product = products.find(p => p.id === selectedProductId);
    if (!product) return;
    
    // Open the modal and show loading spinner
    setIsOrderHistoryModalVisible(true);
    setOrderHistoryLoading(true);
    setOrderHistoryModalTitle(`Impegno corrente per articolo: ${product.code} - ${product.name}`);
    setOrderHistoryData([]); // Clear existing data

    // Fetch order history data
    fetchOrderHistoryData(product.code);
    
    handleMenuClose();
  };

  // Function to fetch order history data
  const fetchOrderHistoryData = async (articleCode) => {
    try {
      // Always use authenticated axios instance for commercial data
      const axiosInstance = createAuthenticatedAxios();
      
      // Fetch data from the backend
      const response = await axiosInstance.get("/article_history", {
        params: { article_code: articleCode },
      });

      const data = response.data;

      if (!Array.isArray(data) || data.length === 0) {
        console.info("No order history data available for this article.");
        setIsOrderHistoryModalVisible(false);
        setOrderHistoryLoading(false);
        return;
      }

      // Process data if necessary
      setOrderHistoryData(data);
    } catch (error) {
      console.error("Error fetching order history data:", error);
      
      // Handle unauthorized errors
      if (error.response && error.response.status === 401) {
        setIsAuthenticated(false);
        localStorage.removeItem('commercialiToken'); // Clear invalid token
        setLoginError('Your session has expired. Please log in again.');
      }
      
      setIsOrderHistoryModalVisible(false);
    } finally {
      setOrderHistoryLoading(false);
    }
  };

  // Define columns for order history table
  const orderHistoryColumns = [
    {
      label: "Articolo",
      key: "mpf_arti",
    },
    {
      label: "Descrizione",
      key: "mpf_desc",
    },
    {
      label: "Data Cons.",
      key: "occ_dtco",
      render: (text) => text ? new Date(text).toLocaleDateString() : "",
    },
    {
      label: "T",
      key: "occ_tipo",
    },
    {
      label: "NrOrd",
      key: "occ_code",
    },
    {
      label: "Stato",
      key: "oct_stap",
      render: (text) => {
        switch (text) {
          case 'A':
            return <span style={{ backgroundColor: '#52c41a', color: 'white', padding: '2px 8px', borderRadius: '4px' }}>Aperto</span>;
          case 'O':
            return <span style={{ backgroundColor: '#1890ff', color: 'white', padding: '2px 8px', borderRadius: '4px' }}>Offerta</span>;
          default:
            return text;
        }
      },
    },
    {
      label: "Cliente",
      key: "oct_cocl",
    },
    {
      label: "Ragione Sociale",
      key: "des_clifor",
    },
    {
      label: "Q.ta totale",
      key: "totale",
    },
    {
      label: "Residuo",
      key: "residuo",
    },
  ];

  // Create axios instance with commercial authentication
  const createAuthenticatedAxios = () => {
    const instance = axios.create({
      baseURL: 'https://api.fecitalia.it',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    });
    return instance;
  };

  // Handle token-based login for commercial products
  const handleLogin = async () => {
    setLoginError(''); // Clear previous errors
    
    try {
      // Use the commercial token endpoint
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await axios.post('https://api.fecitalia.it/tokenCommerciali', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      if (response.data && response.data.access_token) {
        // Store the token
        const token = response.data.access_token;
        setAuthToken(token);
        setIsAuthenticated(true);
        localStorage.setItem('commercialiToken', token); // Store token in local storage for persistence
      } else {
        setLoginError('Authentication failed. Please try again.');
      }
    } catch (error) {
      console.error('Login error:', error);
      
      // Try the fallback validation API if token endpoint fails
      try {
        const validationResponse = await axios.post('https://api.fecitalia.it/validate_commerciali_password', {
          password: password
        });
        
        if (validationResponse.data && validationResponse.data.valid) {
          // For backwards compatibility, mark as authenticated but without a token
          setIsAuthenticated(true);
          
          // Show a warning that token-based auth is preferred
          console.warn('Using fallback authentication. Token-based auth is recommended.');
        } else {
          setLoginError('Invalid password. Please try again.');
        }
      } catch (validationError) {
        console.error('Validation error:', validationError);
        setLoginError('Authentication service unavailable. Please try again later.');
      }
    }
  };
  
  // Check for stored token on component mount
  useEffect(() => {
    const storedToken = localStorage.getItem('commercialiToken');
    if (storedToken) {
      setAuthToken(storedToken);
      setIsAuthenticated(true);
    }
  }, []);
  
  // Only fetch data if authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const fetchData = async () => {
        await fetchProductAvailability();
      };
      
      fetchData();
    }
  }, [isAuthenticated]);

  const fetchProductAvailability = async () => {
    try {
      setLoading(true);
      
      // Always use authenticated axios instance for commercial data
      const axiosInstance = createAuthenticatedAxios();
      
      // Fetch products directly from the articles_commerciali endpoint
      const response = await axiosInstance.get('/articles_commerciali');
      console.log('Articles commerciali API response:', response.data);
      
      // Process the response data
      const commercialArticles = response.data;
      
      // Transform the data into the format expected by the component
      const processedProducts = commercialArticles.map((item, index) => {
        // Trim whitespace from product codes and descriptions
        const productCode = item.c_articolo.trim();
        const productName = item.d_articolo.trim();
        
        return {
          id: index + 1, // Use index as ID if not provided in API
          name: productName,
          code: productCode,
          isMainProduct: true,
          availability: item // Store the full item as availability data
        };
      });
      
      // Sort products by code or name
      processedProducts.sort((a, b) => a.code.localeCompare(b.code));
      
      console.log('Processed products:', processedProducts);
      setProducts(processedProducts);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching products:', error);
      
      // Handle unauthorized errors
      if (error.response && error.response.status === 401) {
        setIsAuthenticated(false);
        localStorage.removeItem('commercialiToken'); // Clear invalid token
        setLoginError('Your session has expired. Please log in again.');
        setError('Authentication required. Please log in again.');
      } else {
        setError('Failed to fetch products. Please try again later.');
      }
      
      setLoading(false);
    }
  };

  // Add a logout function
  const handleLogout = () => {
    setIsAuthenticated(false);
    setAuthToken('');
    localStorage.removeItem('commercialiToken');
  };

  // If not authenticated, show login form
  if (!isAuthenticated) {
    return (
      <Container>
        <LoginCard>
          <CardContent>
            <Typography variant="h5" component="h2" gutterBottom sx={{ textAlign: 'center', color: '#2b2b2b' }}>
              COMMERCIAL PRODUCTS
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
              Please enter the commercial access password
            </Typography>
            
            {loginError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {loginError}
              </Alert>
            )}
            
            <TextField
              fullWidth
              label="Password"
              variant="outlined"
              margin="normal"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleLogin();
                }
              }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
          </CardContent>
          <CardActions>
            <LoginButton
              fullWidth
              variant="contained"
              color="primary"
              onClick={handleLogin}
            >
              Access Commercial Products
            </LoginButton>
          </CardActions>
        </LoginCard>
      </Container>
    );
  }

  return (
    <Box sx={{ bgcolor: 'white', py: 6 }}>
      <Container>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Typography variant="h4" component="h1" sx={{ color: '#2b2b2b', fontWeight: 'bold' }}>
            Commercial Products
          </Typography>
          <Button 
            variant="outlined" 
            color="primary" 
            onClick={handleLogout}
          >
            Log out
          </Button>
        </Box>
        
        <StyledTableContainer component={Paper}>
          <StyledTable aria-label="product availability table">
            <TableHead>
              <TableRow>
                <TableHeaderCell>Action</TableHeaderCell>
                <TableHeaderCell>Codice</TableHeaderCell>
                <TableHeaderCell>Product Name</TableHeaderCell>
                <TableHeaderCell>Today</TableHeaderCell>
                <TableHeaderCell>{currentMonth}</TableHeaderCell>
                <TableHeaderCell>{nextMonth}</TableHeaderCell>
                <TableHeaderCell>{nextPlusTwoMonths}</TableHeaderCell>
                <TableHeaderCell>{nextPlusThreeMonths}</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                // Display loading spinner inside the table spanning all columns
                <TableRow>
                  <TableCell colSpan={8} sx={{ height: '200px', textAlign: 'center' }}>
                    <CircularProgress />
                    <Typography sx={{ mt: 2, color: 'text.secondary' }}>
                      Loading product availability data...
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : error ? (
                // Display error message inside the table
                <TableRow>
                  <TableCell colSpan={8} sx={{ textAlign: 'center', py: 3 }}>
                    <Typography color="error">{error}</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                // Render products with availability data
                products.map((product) => {
                  // Calculate availability values for each time period
                  const todayAvailability = calculateAvailability(product.availability, 'today');
                  const currentMonthAvailability = calculateAvailability(product.availability, 'mc');
                  const nextMonthAvailability = calculateAvailability(product.availability, 'ms');
                  const nextTwoMonthsAvailability = calculateAvailability(product.availability, 'msa');
                  const nextThreeMonthsAvailability = calculateAvailability(product.availability, 'mss');
                  
                  // Standard row for products
                  return (
                    <TableRow key={product.id} hover>
                      <ActionCell>
                        <IconButton
                          aria-label="view details"
                          size="small"
                          onClick={(e) => handleMenuOpen(e, product.id)}
                        >
                          <MoreVert />
                        </IconButton>
                      </ActionCell>
                      <CodeCell>
                        {product.code}
                      </CodeCell>
                      <ProductNameCell component="th" scope="row">
                        {formatProductName(product.name)}
                      </ProductNameCell>
                      <AvailabilityCell>
                        {displayValue(todayAvailability)}
                      </AvailabilityCell>
                      <AvailabilityCell>
                        {displayValue(currentMonthAvailability)}
                      </AvailabilityCell>
                      <AvailabilityCell>
                        {displayValue(nextMonthAvailability)}
                      </AvailabilityCell>
                      <AvailabilityCell>
                        {displayValue(nextTwoMonthsAvailability)}
                      </AvailabilityCell>
                      <AvailabilityCell>
                        {displayValue(nextThreeMonthsAvailability)}
                      </AvailabilityCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </StyledTable>
        </StyledTableContainer>

        {/* Context Menu */}
        <Menu
          anchorEl={menuAnchorEl}
          open={Boolean(menuAnchorEl)}
          onClose={handleMenuClose}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'left',
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'left',
          }}
        >
          <MenuItem onClick={handleViewDetails}>View Details</MenuItem>
          <MenuItem onClick={handleStoricoOrdini}>Impegno corrente</MenuItem>
          <MenuItem onClick={handleExportProduct}>Export</MenuItem>
        </Menu>

        {/* Order History Modal */}
        <Dialog
          open={isOrderHistoryModalVisible}
          onClose={() => setIsOrderHistoryModalVisible(false)}
          maxWidth="lg"
          fullWidth
        >
          <DialogTitle>{orderHistoryModalTitle}</DialogTitle>
          <DialogContent>
            {orderHistoryLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '50px 0' }}>
                <CircularProgress />
                <Typography sx={{ ml: 2 }}>Caricamento impegni articolo...</Typography>
              </Box>
            ) : (
              <TableContainer component={Paper} sx={{ mt: 2 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      {orderHistoryColumns.map((column) => (
                        <TableCell key={column.key} sx={{ fontWeight: 'bold' }}>
                          {column.label}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {orderHistoryData.length > 0 ? (
                      orderHistoryData.map((record, index) => (
                        <TableRow key={index}>
                          {orderHistoryColumns.map((column) => (
                            <TableCell key={`${index}-${column.key}`}>
                              {column.render ? column.render(record[column.key]) : record[column.key]}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={orderHistoryColumns.length} align="center">
                          No data available
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setIsOrderHistoryModalVisible(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </Container>
    </Box>
  );
};

export default ProductsPage; 