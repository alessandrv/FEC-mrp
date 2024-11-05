import React, { useEffect, useState, useMemo } from "react";
import axios from "axios";
import {
  Box,
  CircularProgress,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  Checkbox,
  FormControlLabel,
  Menu,
  MenuItem,
  TextField,
  Switch,
  Radio,
  RadioGroup,
  FormControl,
  FormLabel,
  Button,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  MoreVert as MoreVertIcon,
  MenuFold as MenuFoldIcon,
  Search as SearchIcon,
  Download as DownloadIcon,
} from "@mui/icons-material";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts";
import { DataGrid, GridToolbarContainer } from "@mui/x-data-grid";
import * as XLSX from "xlsx";
import { saveAs } from "file-saver";
import "./InventoryList.css"; // Custom CSS file for styling
// Define custom filter operators
const onlyNegativeOperator = {
  label: 'Solo Negativi',
  value: 'onlyNegative',
  getApplyFilterFn: () => {
    return (params) => {
      return params.value < 0;
    };
  },
  InputComponent: null,
  requiresFilterValue: false,
};

const onlyUnderStockOperator = {
  label: 'Solo Sotto Scorta',
  value: 'onlyUnderStock',
  getApplyFilterFn: (filterItem) => {
    return (params) => {
      return params.value < params.row.scrt;
    };
  },
  InputComponent: null,
  requiresFilterValue: false,
};

// Separate component for the Actions Cell
const ActionsCell = ({ row, handleAPClick, handleStoricoOrdini }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleMenuClick = (option) => {
    if (option === "priceHistory") {
      handleAPClick(row.c_articolo);
    } else if (option === "orderHistory") {
      handleStoricoOrdini(row.c_articolo);
    }
    handleMenuClose();
  };

  return (
    <>
      <IconButton onClick={handleMenuOpen}>
        <MoreVertIcon />
      </IconButton>
      <Menu
        anchorEl={anchorEl}
        open={open}
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
        <MenuItem onClick={() => handleMenuClick("priceHistory")}>
          Storico Prezzi
        </MenuItem>
        <MenuItem onClick={() => handleMenuClick("orderHistory")}>
          Impegno corrente
        </MenuItem>
      </Menu>
    </>
  );
};

// Custom Toolbar with Radio Buttons for Filtering
const CustomToolbar = ({ setFilter }) => {
  const handleFilterChange = (event) => {
    const value = event.target.value;
    setFilter(value);
  };

  return (
    <GridToolbarContainer>
      <FormControl component="fieldset" sx={{ margin: 2 }}>
        <FormLabel component="legend">Disponibilità Filter</FormLabel>
        <RadioGroup row onChange={handleFilterChange} defaultValue="all">
          <FormControlLabel value="all" control={<Radio />} label="Tutti" />
          <FormControlLabel value="negative" control={<Radio />} label="Solo Negativi" />
          <FormControlLabel value="underStock" control={<Radio />} label="Solo Sotto Scorta" />
        </RadioGroup>
      </FormControl>
    </GridToolbarContainer>
  );
};

const ArticlesTable = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isPriceModalOpen, setIsPriceModalOpen] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartData, setChartData] = useState([]);
  const [modalTitle, setModalTitle] = useState("");
  const [maxPriceData, setMaxPriceData] = useState(null);
  const [minPriceData, setMinPriceData] = useState(null);
  const [isAverage, setIsAverage] = useState(false);
  const [rawChartData, setRawChartData] = useState([]);
  const [averageChartData, setAverageChartData] = useState([]);
  const [valuta, setValuta] = useState(null);
  const [isOrderHistoryModalOpen, setIsOrderHistoryModalOpen] = useState(false);
  const [orderHistoryData, setOrderHistoryData] = useState([]);
  const [orderHistoryLoading, setOrderHistoryLoading] = useState(false);
  const [orderHistoryModalTitle, setOrderHistoryModalTitle] = useState("");
  const [searchText, setSearchText] = useState("");
  const [apFilter, setApFilter] = useState("A");
  const [filterOption, setFilterOption] = useState('all');

  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "error",
  });

  // Fetch data from the FastAPI backend
  const parseIntegerData = (data) => {
    // Function to calculate availability
    const calculateAvailability = (record, month) => {
      const giacD01 = record.giac_d01 || 0;
  
      if (month === "mc") {
        // First month (m corr.) starts from the D01 value
        return giacD01 - (record.dom_mc || 0) + (record.off_mc || 0);
      } else if (month === "ms") {
        // Next month (m succ.) starts from Disponibilità m corr.
        const currentMonthAvailability = giacD01 - (record.dom_mc || 0) + (record.off_mc || 0);
        return currentMonthAvailability - (record.dom_ms || 0) + (record.off_ms || 0);
      } else if (month === "msa") {
        // Following month (2m succ.) starts from Disponibilità m succ.
        const nextMonthAvailability = (giacD01 - (record.dom_mc || 0) + (record.off_mc || 0)) 
                                      - (record.dom_ms || 0) + (record.off_ms || 0);
        return nextMonthAvailability - (record.dom_msa || 0) + (record.off_msa || 0);
      }
      return 0; // Default for undefined month parameter
    };
  
    return data.map((item) => ({
      ...item,
      c_articolo: item.c_articolo, // Articolo remains as a string
      a_p: item.a_p,               // AP remains as a string
      d_articolo: item.d_articolo, // Descrizione as a string
      lt: parseInt(item.lt) || 0,
      scrt: parseInt(item.scrt) || 0,
      giac_d01: parseInt(item.giac_d01) || 0,
      giac_d20: parseInt(item.giac_d20) || 0,
      giac_d32: parseInt(item.giac_d32) || 0,
      giac_d48: parseInt(item.giac_d48) || 0,
      giac_d60: parseInt(item.giac_d60) || 0,
      giac_d81: parseInt(item.giac_d81) || 0,
      ord_mpp: parseInt(item.ord_mpp) || 0,
      ord_mp: parseInt(item.ord_mp) || 0,
      ord_mc: parseInt(item.ord_mc) || 0,
      dom_mc: parseInt(item.dom_mc) || 0,
      dom_ms: parseInt(item.dom_ms) || 0,
      dom_msa: parseInt(item.dom_msa) || 0,
      dom_mss: parseInt(item.dom_mss) || 0,
      off_mc: parseInt(item.off_mc) || 0,
      off_ms: parseInt(item.off_ms) || 0,
      off_msa: parseInt(item.off_msa) || 0,
      off_mss: parseInt(item.off_mss) || 0,
      // Precompute Disponibilità fields
      disponibilita_m_corr: calculateAvailability(item, "mc"),
      disponibilita_m_succ: calculateAvailability(item, "ms"),
      disponibilita_2m_succ: calculateAvailability(item, "msa"),
    }));
  };
  

  useEffect(() => {
    const errorHandler = (e) => {
      if (
        e.message.includes("ResizeObserver loop completed with undelivered notifications") ||
        e.message.includes("ResizeObserver loop limit exceeded")
      ) {
        const resizeObserverErr = document.getElementById(
          "webpack-dev-server-client-overlay"
        );
        if (resizeObserverErr) {
          resizeObserverErr.style.display = "none";
        }
      }
    };
    window.addEventListener("error", errorHandler);
    return () => {
      window.removeEventListener("error", errorHandler);
    };
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get("http://172.16.16.69:8000/articles");
        let fetchedData = parseIntegerData(response.data);

        // Sort the data based on 'c_articolo'
        fetchedData.sort((a, b) => a.c_articolo.localeCompare(b.c_articolo));

        setData(fetchedData);
      } catch (error) {
        setSnackbar({
          open: true,
          message: "Failed to fetch data from the server.",
          severity: "error",
        });
        console.error("Error fetching data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const handleStoricoOrdini = (articleCode) => {
    // Open the modal and show loading spinner
    setIsOrderHistoryModalOpen(true);
    setOrderHistoryLoading(true);
    setOrderHistoryModalTitle(`Impegno corrente per articolo: ${articleCode}`);
    setOrderHistoryData([]); // Clear existing data

    // Fetch order history data
    fetchOrderHistoryData(articleCode);
  };

  const fetchOrderHistoryData = async (articleCode) => {
    try {
      // Fetch data from the backend
      const response = await axios.get("http://172.16.16.69:8000/article_history", {
        params: { article_code: articleCode },
      });

      const data = response.data;

      if (!Array.isArray(data) || data.length === 0) {
        setSnackbar({
          open: true,
          message: "No order history data available for this article.",
          severity: "info",
        });
        setIsOrderHistoryModalOpen(false);
        setOrderHistoryLoading(false);
        return;
      }

      // Process data if necessary
      setOrderHistoryData(data);
    } catch (error) {
      setSnackbar({
        open: true,
        message: "Impossibile trovare Impegno corrente.",
        severity: "error",
      });
      console.error("Error fetching order history data:", error);
      setIsOrderHistoryModalOpen(false);
    } finally {
      setOrderHistoryLoading(false);
    }
  };

  const handleAPClick = (articleCode) => {
    // Open the modal and show loading spinner
    setIsPriceModalOpen(true);
    setChartLoading(true);
    setModalTitle(`Storico prezzi per articolo: ${articleCode}`);
    setIsAverage(false); // Reset checkbox state
    setChartData([]); // Clear existing chart data
    setRawChartData([]);
    setAverageChartData([]);
    setMaxPriceData(null);
    setMinPriceData(null);
    setValuta(null);

    // Use setTimeout to delay the data fetching
    setTimeout(() => {
      fetchArticleData(articleCode);
    }, 0);
  };

  const fetchArticleData = async (articleCode) => {
    try {
      console.time('Total fetchArticleData time');

      console.time('API call time');
      // Fetch processed data from the backend
      const response = await axios.get("http://172.16.16.69:8000/article_price", {
        params: { article_code: articleCode },
      });
      console.timeEnd('API call time');

      console.time('Data processing time');
      const {
        rawData,
        averageData,
        valuta,
        maxPriceData,
        minPriceData,
      } = response.data;

      if (rawData.length === 0) {
        setSnackbar({
          open: true,
          message: "No price data available for this article.",
          severity: "info",
        });
        setIsPriceModalOpen(false);
        setChartLoading(false);
        console.timeEnd('Data processing time');
        console.timeEnd('Total fetchArticleData time');
        return;
      }

      console.log('Number of records in rawData:', rawData.length);
      console.log('Number of records in averageData:', averageData.length);

      // Measure time to set state
      console.time('setState time');
      setRawChartData(rawData);
      setAverageChartData(averageData);

      // Initially show raw data
      setChartData(rawData);

      // Set max and min price data
      setMaxPriceData(maxPriceData);
      setMinPriceData(minPriceData);

      setValuta(valuta);
      console.timeEnd('setState time');

      // Measure time to set chart loading
      console.time('setChartLoading time');
      setChartLoading(false);
      console.timeEnd('setChartLoading time');

      console.timeEnd('Data processing time');
      console.timeEnd('Total fetchArticleData time');

    } catch (error) {
      setSnackbar({
        open: true,
        message: "Impossibile trovare storico prezzi.",
        severity: "error",
      });
      console.error("Error fetching article price data:", error);
      setIsPriceModalOpen(false);
      setChartLoading(false);
      console.timeEnd('Data processing time');
      console.timeEnd('Total fetchArticleData time');
    }
  };

  const handleCheckboxChange = (e) => {
    const average = e.target.checked;
    setIsAverage(average);
    updateChartData(average);
  };

  const updateChartData = (average) => {
    if (average) {
      // In average mode, dates represent months
      setChartData(averageChartData);

      // Compute max and min values for average data
      const maxPrice = averageChartData.reduce(
        (max, item) => (item.price > max.price ? item : max),
        averageChartData[0]
      );

      const minPrice = averageChartData.reduce(
        (min, item) => (item.price < min.price ? item : min),
        averageChartData[0]
      );

      setMaxPriceData(maxPrice);
      setMinPriceData(minPrice);
    } else {
      // In raw mode, dates represent individual dates
      setChartData(rawChartData);

      // Compute max and min values for raw data
      const maxPrice = rawChartData.reduce(
        (max, item) => (item.price > max.price ? item : max),
        rawChartData[0]
      );

      const minPrice = rawChartData.reduce(
        (min, item) => (item.price < min.price ? item : min),
        rawChartData[0]
      );

      setMaxPriceData(maxPrice);
      setMinPriceData(minPrice);
    }
  };

  // Calculate current month's availability
  const calculateAvailability = (record, month) => {
    const giacD01 = record.giac_d01 || 0;

    if (month === "mc") {
      // First month (m corr.) starts from the D01 value
      return giacD01 - (record.dom_mc || 0) + (record.off_mc || 0);
    } else if (month === "ms") {
      // Next month (m succ.) starts from Disponibilità m corr.
      const currentMonthAvailability = calculateAvailability(record, "mc");
      return currentMonthAvailability - (record.dom_ms || 0) + (record.off_ms || 0);
    } else if (month === "msa") {
      // Following month (2m succ.) starts from Disponibilità m succ.
      const nextMonthAvailability = calculateAvailability(record, "ms");
      return nextMonthAvailability - (record.dom_msa || 0) + (record.off_msa || 0);
    }
    return 0; // Default for undefined month parameter
  };

  const getAvailabilityCellClass = (value, scorta) => {
    if (value < 0) {
      return "cell-red";
    } else if (value < scorta) {
      return "cell-yellow";
    }
    return "cell-default";
  };

  // Define columns for the main DataGrid
  const columns = [
    {
      field: "actions",
      headerName: "",
      width: 50,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <ActionsCell
          row={params.row}
          handleAPClick={handleAPClick}
          handleStoricoOrdini={handleStoricoOrdini}
        />
      ),
    },
    {
      field: "c_articolo",
      headerName: "Articolo",
      width: 150,
      renderCell: (params) => <strong>{params.value}</strong>,
      sortable: true,
      filterable: true,
    },
    {
      field: "a_p",
      headerName: "AP",
      width: 100,
      sortable: true,
      filterable: true,
      // Implement custom filter if needed
      filterOperators: [
        {
          label: 'A',
          value: 'A',
          getApplyFilterFn: () => {
            return (params) => params.value === 'A';
          },
          InputComponent: null,
          requiresFilterValue: false,
        },
        {
          label: 'P',
          value: 'P',
          getApplyFilterFn: () => {
            return (params) => params.value === 'P';
          },
          InputComponent: null,
          requiresFilterValue: false,
        },
      ],
    },
    {
      field: "d_articolo",
      headerName: "Descrizione",
      width: 200,
      sortable: true,
      filterable: true,
    },
    {
      field: "lt",
      headerName: "LT",
      width: 100,
      type: 'number',
      sortable: true,
      filterable: true,
    },
    {
      field: "scrt",
      headerName: "SCRT",
      width: 100,
      type: 'number',
      sortable: true,
      filterable: true,
    },
    {
      field: "giac_d01",
      headerName: "Dep. 1",
      width: 100,
      type: 'number',
      sortable: true,
      filterable: true,
    },
    {
      field: "giac_d20",
      headerName: "Dep. 20",
      width: 100,
      type: 'number',
      sortable: true,
      filterable: true,
    },
    {
      field: "giac_d32",
      headerName: "Dep. 32",
      width: 100,
      type: 'number',
      sortable: true,
      filterable: true,
    },
    {
      field: "giac_d48",
      headerName: "Dep. 48",
      width: 100,
      type: 'number',
      sortable: true,
      filterable: true,
    },
    {
      field: "giac_d60",
      headerName: "Dep. 60",
      width: 100,
      type: 'number',
      sortable: true,
      filterable: true,
    },
    {
      field: "giac_d81",
      headerName: "Dep. 81",
      width: 100,
      type: 'number',
      sortable: true,
      filterable: true,
    },
    {
      field: "disponibilita_m_corr",
      headerName: "Disp. m corr.",
      width: 150,
      type: 'number',
      sortable: true,
      filterable: true,
      filterOperators: [onlyNegativeOperator, onlyUnderStockOperator],
      renderCell: (params) => {
        const value = params.value;
        const cellClass = getAvailabilityCellClass(value, params.row.scrt);
        return (
          <Box className={cellClass}>
            {value}
          </Box>
        );
      },
    },
    {
      field: "disponibilita_m_succ",
      headerName: "Disp. m succ.",
      width: 150,
      type: 'number',
      sortable: true,
      filterable: true,
      filterOperators: [onlyNegativeOperator, onlyUnderStockOperator],
      renderCell: (params) => {
        const value = params.value;
        const cellClass = getAvailabilityCellClass(value, params.row.scrt);
        return (
          <Box className={cellClass}>
            {value}
          </Box>
        );
      },
    },
    {
      field: "disponibilita_2m_succ",
      headerName: "Disp. 2m succ.",
      width: 150,
      type: 'number',
      sortable: true,
      filterable: true,
      filterOperators: [onlyNegativeOperator, onlyUnderStockOperator],
      renderCell: (params) => {
        const value = params.value;
        const cellClass = getAvailabilityCellClass(value, params.row.scrt);
        return (
          <Box className={cellClass}>
            {value}
          </Box>
        );
      },
    },
    // ... Add other fields similarly
    {
      field: "ord_mpp",
      headerName: "Ordine 2m prec.",
      width: 150,
      type: 'number',
    },
    {
      field: "ord_mp",
      headerName: "Ordine m prec.",
      width: 150,
      type: 'number',
    },
    {
      field: "ord_mc",
      headerName: "Ordine m corr.",
      width: 150,
      type: 'number',
    },
    {
      field: "dom_mc",
      headerName: "Impegno m corr.",
      width: 150,
      type: 'number',
    },
    {
      field: "dom_ms",
      headerName: "Impegno m succ.",
      width: 150,
      type: 'number',
    },
    {
      field: "dom_msa",
      headerName: "Impegno 2m succ.",
      width: 150,
      type: 'number',
    },
    {
      field: "dom_mss",
      headerName: "Impegno 3m+ succ.",
      width: 150,
      type: 'number',
    },
    {
      field: "off_mc",
      headerName: "Atteso m corr.",
      width: 150,
      type: 'number',
    },
    {
      field: "off_ms",
      headerName: "Atteso m succ.",
      width: 150,
      type: 'number',
    },
    {
      field: "off_msa",
      headerName: "Atteso 2m succ.",
      width: 150,
      type: 'number',
    },
    {
      field: "off_mss",
      headerName: "Atteso 3m+ succ.",
      width: 150,
      type: 'number',
    },
  ];
  

  const exportExcel = () => {
    // Define the columns to include in the export
    const exportData = data.map((item) => ({
      "Articolo": item.c_articolo,
      "AP": item.a_p,
      "Descrizione": item.d_articolo,
      "LT": item.lt,
      "SCRT": item.scrt,
      "Dep. 1": item.giac_d01,
      "Dep. 20": item.giac_d20,
      "Dep. 32": item.giac_d32,
      "Dep. 48": item.giac_d48,
      "Dep. 60": item.giac_d60,
      "Dep. 81": item.giac_d81,
      "Disponibilità m corr.": calculateAvailability(item, "mc"),
      "Disponibilità m succ.": calculateAvailability(item, "ms"),
      "Disponibilità 2m succ.": calculateAvailability(item, "msa"),
      "Ordine 2m prec.": item.ord_mpp,
      "Ordine m prec.": item.ord_mp,
      "Ordine m corr.": item.ord_mc,
      "Impegno m corr.": item.dom_mc,
      "Impegno m succ.": item.dom_ms,
      "Impegno 2m succ.": item.dom_msa,
      "Impegno 3m+ succ.": item.dom_mss,
      "Atteso m corr.": item.off_mc,
      "Atteso m succ.": item.off_ms,
      "Atteso 2m succ.": item.off_msa,
      "Atteso 3m+ succ.": item.off_mss,
    }));

    // Create a worksheet from the data
    const worksheet = XLSX.utils.json_to_sheet(exportData);

    // Create a new workbook and append the worksheet
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Articoli");

    // Generate a buffer
    const excelBuffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });

    // Create a Blob from the buffer
    const dataBlob = new Blob([excelBuffer], { type: "application/octet-stream" });

    // Trigger the download using FileSaver
    saveAs(dataBlob, "Articoli.xlsx");
  };

  // Custom Legend Component
  const CustomLegend = () => {
    return (
      <Box sx={{ textAlign: "left", marginLeft: 2 }}>
        <Box>
          <strong>Valuta:</strong> {valuta}
        </Box>
        <Box>
          <strong>Max:</strong> {maxPriceData.price.toFixed(2)} - {new Date(maxPriceData.date).toLocaleDateString()}
        </Box>
        <Box>
          <strong>Min:</strong> {minPriceData.price.toFixed(2)} - {new Date(minPriceData.date).toLocaleDateString()}
        </Box>

        <FormControlLabel
          control={
            <Checkbox
              checked={isAverage}
              onChange={handleCheckboxChange}
            />
          }
          label="Media per mese"
          sx={{ marginTop: 1 }}
        />
      </Box>
    );
  };

  return (
    <Box className="table-container" sx={{ padding: 2 }}>
      {/* Export Button */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 2 }}>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={exportExcel}
        >
          Esporta Excel
        </Button>
      </Box>

      {/* Main Data Grid */}
      <Box sx={{ height: 680, width: '100%' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid
            rows={data}
            columns={columns}
            getRowId={(row) => row.c_articolo}
            pageSize={1000}
            rowsPerPageOptions={[10, 20, 50, 100, 1000, 10000]}
            pagination
            disableSelectionOnClick
            components={{
              Toolbar: CustomToolbar, // Use the custom toolbar with radio buttons
            }}
            componentsProps={{
              toolbar: { setFilter: setFilterOption },
            }}
            sx={{
              '& .cell-red': {
                backgroundColor: '#ffcccc',
              },
              '& .cell-yellow': {
                backgroundColor: '#fff0b3',
              },
              '& .cell-default': {
                backgroundColor: '#f0f0f0',
              },
            }}
          />
        )}
      </Box>

      {/* Snackbar for Notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>

      {/* Modal for displaying the line chart */}
      <Dialog
        open={isPriceModalOpen}
        onClose={() => setIsPriceModalOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>{modalTitle}</DialogTitle>
        <DialogContent>
          {chartLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box>
              <Box sx={{ display: "flex", justifyContent: "center", marginBottom: 2 }}>
                <LineChart
                  width={800}
                  height={500}
                  data={chartData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 50 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    angle={-45}
                    textAnchor="end"
                    tickFormatter={(dateValue) => {
                      if (isAverage) {
                        // In average mode, dateValue represents a month string like '2023-10'
                        const date = new Date(dateValue + '-01'); // Append '-01' to create a valid date
                        return date.toLocaleString('default', { month: 'short', year: 'numeric' });
                      } else {
                        // In raw mode, dateValue is an ISO date string or Date object
                        const date = new Date(dateValue);
                        return date.toLocaleDateString(); // Format as 'MM/DD/YYYY' or your locale format
                      }
                    }}
                  />
                  <YAxis />
                  <RechartsTooltip
                    labelFormatter={(dateStr) => {
                      const date = new Date(dateStr);
                      return date.toLocaleDateString();
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke="#8884d8"
                    activeDot={{ r: 8 }}
                  />
                  {/* Include the custom legend */}
                  {maxPriceData && minPriceData && (
                    <Legend
                      verticalAlign="middle"
                      align="right"
                      layout="vertical"
                      content={<CustomLegend />}
                    />
                  )}
                </LineChart>
              </Box>
            </Box>
          )}
        </DialogContent>
      </Dialog>

      {/* Modal for displaying the order history */}
      <Dialog
        open={isOrderHistoryModalOpen}
        onClose={() => setIsOrderHistoryModalOpen(false)}
        fullWidth
        maxWidth="xl"
      >
        <DialogTitle>{orderHistoryModalTitle}</DialogTitle>
        <DialogContent>
          {orderHistoryLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box sx={{ height: 500, width: '100%' }}>
              <DataGrid
                rows={orderHistoryData}
                columns={[
                  { field: 'mpf_arti', headerName: 'Articolo', width: 150 },
                  { field: 'mpf_desc', headerName: 'Descrizione', width: 200 },
                  {
                    field: 'occ_dtco',
                    headerName: 'DataCons',
                    width: 150,
                    type: 'date',
                    valueGetter: (params) => params.value ? new Date(params.value) : null,
                  },
                  { field: 'occ_tipo', headerName: 'T', width: 100 },
                  { field: 'occ_code', headerName: 'NrOrd', width: 150 },
                  { field: 'oct_cocl', headerName: 'Cliente', width: 150 },
                  { field: 'des_clifor', headerName: 'Ragione Sociale', width: 200 },
                  { field: 'quantity', headerName: 'Q.ta', width: 100, type: 'number' },
                  { field: 'residuo', headerName: 'Residuo', width: 100, type: 'number' },
                ]}
                getRowId={(row, index) => index}
                pageSize={10}
                rowsPerPageOptions={[10, 20, 50, 10000]}
                pagination
                disableSelectionOnClick
              />
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default ArticlesTable;
