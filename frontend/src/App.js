import React, { useState, useCallback, useRef } from 'react';
import { Upload, Download, Settings, Trash2, FileImage, FileVideo, FileAudio, FileText, CheckCircle, AlertCircle, Loader } from 'lucide-react';

const FileCompressorApp = () => {
  const [files, setFiles] = useState([]);
  const [taskId, setTaskId] = useState(null);
  const [compressionStatus, setCompressionStatus] = useState(null);
  const [settings, setSettings] = useState({
    quality: 85,
    video_bitrate: '1000k',
    audio_bitrate: '128k',
    max_width: 1920,
    max_height: 1080
  });
  const [isUploading, setIsUploading] = useState(false);
  const [isCompressing, setIsCompressing] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const fileInputRef = useRef(null);
  const pollInterval = useRef(null);

  const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:5000' : '';

  const formatFileSize = (bytes) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getFileIcon = (filename) => {
    const ext = filename.toLowerCase().split('.').pop();
    if (['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'heic', 'heif'].includes(ext)) {
      return <FileImage className="w-6 h-6 text-blue-500" />;
    }
    if (['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'].includes(ext)) {
      return <FileVideo className="w-6 h-6 text-red-500" />;
    }
    if (['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'].includes(ext)) {
      return <FileAudio className="w-6 h-6 text-green-500" />;
    }
    if (ext === 'pdf') {
      return <FileText className="w-6 h-6 text-orange-500" />;
    }
    return <FileText className="w-6 h-6 text-gray-500" />;
  };

  const handleFileSelect = (event) => {
    const selectedFiles = Array.from(event.target.files);
    setFiles(selectedFiles);
  };

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    const droppedFiles = Array.from(event.dataTransfer.files);
    setFiles(droppedFiles);
  }, []);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
  }, []);

  const uploadFiles = async () => {
    if (files.length === 0) return;

    setIsUploading(true);
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    try {
      const response = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        setTaskId(result.task_id);
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Error uploading files:', error);
      alert('Erreur lors de l\'upload des fichiers');
    } finally {
      setIsUploading(false);
    }
  };

  const startCompression = async () => {
    if (!taskId) return;

    setIsCompressing(true);
    try {
      const response = await fetch(`${API_BASE}/api/compress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, settings })
      });

      if (response.ok) {
        startPolling();
      } else {
        throw new Error('Compression start failed');
      }
    } catch (error) {
      console.error('Error starting compression:', error);
      alert('Erreur lors du démarrage de la compression');
      setIsCompressing(false);
    }
  };

  const startPolling = () => {
    pollInterval.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/api/status/${taskId}`);
        if (response.ok) {
          const status = await response.json();
          setCompressionStatus(status);

          if (status.status === 'completed' || status.status === 'error') {
            clearInterval(pollInterval.current);
            setIsCompressing(false);
          }
        }
      } catch (error) {
        console.error('Error polling status:', error);
      }
    }, 1000);
  };

  const downloadFiles = async () => {
    if (!taskId) return;

    try {
      const response = await fetch(`${API_BASE}/api/download/${taskId}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `compressed_files_${taskId.slice(0, 8)}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error downloading files:', error);
      alert('Erreur lors du téléchargement');
    }
  };

  const resetApp = () => {
    setFiles([]);
    setTaskId(null);
    setCompressionStatus(null);
    setIsUploading(false);
    setIsCompressing(false);
    if (pollInterval.current) {
      clearInterval(pollInterval.current);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const calculateTotalSavings = () => {
    if (!compressionStatus || !compressionStatus.results) return null;
    
    const successful = compressionStatus.results.filter(r => r.status === 'success');
    const totalOriginal = successful.reduce((sum, r) => sum + r.original_size, 0);
    const totalCompressed = successful.reduce((sum, r) => sum + r.compressed_size, 0);
    const savings = totalOriginal - totalCompressed;
    const percentage = totalOriginal > 0 ? (savings / totalOriginal) * 100 : 0;
    
    return { savings, percentage, totalOriginal, totalCompressed };
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Compresseur de Fichiers
          </h1>
          <p className="text-gray-600">
            Compressez vos images, vidéos, audio et PDF en toute simplicité
          </p>
        </div>

        {/* Upload Zone */}
        {!taskId && (
          <div className="max-w-4xl mx-auto">
            <div
              className="border-2 border-dashed border-blue-300 rounded-lg p-12 text-center bg-white/50 backdrop-blur-sm hover:border-blue-400 transition-colors cursor-pointer"
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="w-16 h-16 text-blue-500 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-700 mb-2">
                Glissez vos fichiers ici ou cliquez pour sélectionner
              </h3>
              <p className="text-gray-500 mb-4">
                Supports: Images, Vidéos, Audio, PDF (Max: 500MB)
              </p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept=".jpg,.jpeg,.png,.webp,.bmp,.tiff,.heic,.heif,.mp4,.avi,.mov,.mkv,.wmv,.flv,.mp3,.wav,.flac,.aac,.ogg,.m4a,.pdf"
              />
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="mt-6 bg-white/70 backdrop-blur-sm rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">
                  Fichiers sélectionnés ({files.length})
                </h3>
                
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                      {getFileIcon(file.name)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Actions */}
                <div className="flex justify-between items-center mt-6 pt-4 border-t">
                  <button
                    onClick={() => setShowSettings(!showSettings)}
                    className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                    <span>Paramètres</span>
                  </button>

                  <div className="space-x-3">
                    <button
                      onClick={resetApp}
                      className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                    >
                      Annuler
                    </button>
                    <button
                      onClick={uploadFiles}
                      disabled={isUploading}
                      className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isUploading ? 'Upload...' : 'Continuer'}
                    </button>
                  </div>
                </div>

                {/* Settings Panel */}
                {showSettings && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium mb-3">Paramètres de compression</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Qualité image (1-100)
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="100"
                          value={settings.quality}
                          onChange={(e) => setSettings({...settings, quality: parseInt(e.target.value)})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Bitrate vidéo
                        </label>
                        <select
                          value={settings.video_bitrate}
                          onChange={(e) => setSettings({...settings, video_bitrate: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="500k">500k (Faible)</option>
                          <option value="1000k">1000k (Moyen)</option>
                          <option value="2000k">2000k (Élevé)</option>
                        </select>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Compression Status */}
        {taskId && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white/70 backdrop-blur-sm rounded-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold">État de la compression</h3>
                <button
                  onClick={resetApp}
                  className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Nouveau</span>
                </button>
              </div>

              {!compressionStatus && (
                <div className="text-center py-8">
                  <button
                    onClick={startCompression}
                    disabled={isCompressing}
                    className="bg-green-500 hover:bg-green-600 text-white px-8 py-3 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isCompressing ? 'Démarrage...' : 'Démarrer la compression'}
                  </button>
                </div>
              )}

              {compressionStatus && (
                <div className="space-y-4">
                  {/* Progress Bar */}
                  {compressionStatus.status === 'processing' && (
                    <div className="mb-6">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-gray-700">
                          Progression
                        </span>
                        <span className="text-sm text-gray-600">
                          {compressionStatus.processed_files}/{compressionStatus.total_files} fichiers
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${compressionStatus.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Results Summary */}
                  {compressionStatus.status === 'completed' && (() => {
                    const savings = calculateTotalSavings();
                    return savings && (
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                        <div className="flex items-center space-x-2 mb-2">
                          <CheckCircle className="w-5 h-5 text-green-500" />
                          <h4 className="font-semibold text-green-800">Compression terminée</h4>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-gray-600">Taille originale:</span>
                            <div className="font-medium">{formatFileSize(savings.totalOriginal)}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Taille compressée:</span>
                            <div className="font-medium">{formatFileSize(savings.totalCompressed)}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Économie:</span>
                            <div className="font-medium text-green-600">{formatFileSize(savings.savings)}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Réduction:</span>
                            <div className="font-medium text-green-600">{savings.percentage.toFixed(1)}%</div>
                          </div>
                        </div>
                      </div>
                    );
                  })()}

                  {/* File Results */}
                  {compressionStatus.results && compressionStatus.results.length > 0 && (
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {compressionStatus.results.map((result, index) => (
                        <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                          {getFileIcon(result.filename)}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {result.filename}
                            </p>
                            {result.status === 'success' ? (
                              <p className="text-xs text-gray-500">
                                {formatFileSize(result.original_size)} → {formatFileSize(result.compressed_size)} 
                                <span className="text-green-600 ml-2">
                                  (-{result.compression_ratio.toFixed(1)}%)
                                </span>
                              </p>
                            ) : (
                              <p className="text-xs text-red-500">{result.error}</p>
                            )}
                          </div>
                          <div>
                            {result.status === 'success' ? (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            ) : (
                              <AlertCircle className="w-5 h-5 text-red-500" />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Download Button */}
                  {compressionStatus.status === 'completed' && (
                    <div className="text-center pt-4">
                      <button
                        onClick={downloadFiles}
                        className="bg-blue-500 hover:bg-blue-600 text-white px-8 py-3 rounded-lg font-medium transition-colors flex items-center space-x-2 mx-auto"
                      >
                        <Download className="w-5 h-5" />
                        <span>Télécharger les fichiers compressés</span>
                      </button>
                    </div>
                  )}

                  {/* Processing Indicator */}
                  {compressionStatus.status === 'processing' && (
                    <div className="text-center py-4">
                      <Loader className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-2" />
                      <p className="text-gray-600">Compression en cours...</p>
                    </div>
                  )}

                  {/* Error State */}
                  {compressionStatus.status === 'error' && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <div className="flex items-center space-x-2">
                        <AlertCircle className="w-5 h-5 text-red-500" />
                        <h4 className="font-semibold text-red-800">Erreur de compression</h4>
                      </div>
                      <p className="text-red-700 mt-2">{compressionStatus.error_message}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-12 text-gray-500">
          <p>Compresseur de fichiers - Sécurisé et efficace</p>
          <p className="text-sm mt-1">Vos fichiers sont traités localement et supprimés automatiquement</p>
        </div>
      </div>
    </div>
  );
};

export default FileCompressorApp;