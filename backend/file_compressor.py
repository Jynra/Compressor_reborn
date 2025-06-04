#!/usr/bin/env python3
"""
Compresseur de fichiers multimédia
Supporte: PDF, Images (JPEG, PNG, WebP), Vidéos (MP4, AVI, MOV), Audio (MP3, WAV, FLAC)
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Tuple, Optional
import shutil

# Importation des bibliothèques (à installer avec pip)
try:
    from PIL import Image, ImageOps
    from PyPDF2 import PdfReader, PdfWriter
    import moviepy.editor as mp
    from pydub import AudioSegment
    import pillow_heif
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Installez les dépendances avec:")
    print("pip install Pillow PyPDF2 moviepy pydub pillow-heif")
    sys.exit(1)

# Enregistrer les formats HEIF/HEIC
pillow_heif.register_heif_opener()

class FileCompressor:
    """Classe principale pour la compression de fichiers"""
    
    def __init__(self, output_dir: str = "compressed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Extensions supportées
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.heic', '.heif'}
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
        self.audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
        self.pdf_extensions = {'.pdf'}
    
    def get_file_size(self, filepath: Path) -> int:
        """Retourne la taille du fichier en octets"""
        return filepath.stat().st_size
    
    def format_size(self, size_bytes: int) -> str:
        """Formate la taille en unités lisibles"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def compress_image(self, input_path: Path, quality: int = 85, max_resolution: Tuple[int, int] = (1920, 1080)) -> Optional[Path]:
        """Compresse une image"""
        try:
            with Image.open(input_path) as img:
                # Convertir en RGB si nécessaire
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Redimensionner si nécessaire
                img.thumbnail(max_resolution, Image.Resampling.LANCZOS)
                
                # Optimiser l'orientation
                img = ImageOps.exif_transpose(img)
                
                # Déterminer le format de sortie
                output_format = 'JPEG'
                if input_path.suffix.lower() == '.png':
                    output_format = 'PNG'
                elif input_path.suffix.lower() == '.webp':
                    output_format = 'WebP'
                
                # Créer le nom de fichier de sortie
                output_path = self.output_dir / f"{input_path.stem}_compressed{input_path.suffix}"
                
                # Sauvegarder l'image compressée
                save_kwargs = {'optimize': True}
                if output_format == 'JPEG':
                    save_kwargs['quality'] = quality
                elif output_format == 'WebP':
                    save_kwargs['quality'] = quality
                
                img.save(output_path, format=output_format, **save_kwargs)
                return output_path
                
        except Exception as e:
            print(f"Erreur lors de la compression de l'image {input_path}: {e}")
            return None
    
    def compress_pdf(self, input_path: Path) -> Optional[Path]:
        """Compresse un PDF en supprimant les métadonnées et en optimisant"""
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Copier toutes les pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Supprimer les métadonnées
            writer.add_metadata({})
            
            # Créer le nom de fichier de sortie
            output_path = self.output_dir / f"{input_path.stem}_compressed.pdf"
            
            # Sauvegarder le PDF compressé
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path
            
        except Exception as e:
            print(f"Erreur lors de la compression du PDF {input_path}: {e}")
            return None
    
    def compress_video(self, input_path: Path, bitrate: str = "1000k", resolution: Tuple[int, int] = (1280, 720)) -> Optional[Path]:
        """Compresse une vidéo"""
        try:
            # Charger la vidéo
            video = mp.VideoFileClip(str(input_path))
            
            # Redimensionner si nécessaire
            if video.w > resolution[0] or video.h > resolution[1]:
                video = video.resize(newsize=resolution)
            
            # Créer le nom de fichier de sortie
            output_path = self.output_dir / f"{input_path.stem}_compressed.mp4"
            
            # Sauvegarder la vidéo compressée
            video.write_videofile(
                str(output_path),
                bitrate=bitrate,
                audio_bitrate="128k",
                temp_audiofile="temp-audio.m4a",
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            video.close()
            return output_path
            
        except Exception as e:
            print(f"Erreur lors de la compression de la vidéo {input_path}: {e}")
            return None
    
    def compress_audio(self, input_path: Path, bitrate: str = "128k", format: str = "mp3") -> Optional[Path]:
        """Compresse un fichier audio"""
        try:
            # Charger le fichier audio
            audio = AudioSegment.from_file(input_path)
            
            # Réduire la qualité si nécessaire
            if audio.frame_rate > 44100:
                audio = audio.set_frame_rate(44100)
            
            # Créer le nom de fichier de sortie
            output_path = self.output_dir / f"{input_path.stem}_compressed.{format}"
            
            # Sauvegarder l'audio compressé
            audio.export(
                output_path,
                format=format,
                bitrate=bitrate,
                parameters=["-q:a", "2"]  # Qualité variable pour MP3
            )
            
            return output_path
            
        except Exception as e:
            print(f"Erreur lors de la compression de l'audio {input_path}: {e}")
            return None
    
    def compress_file(self, input_path: Path, **kwargs) -> Optional[Path]:
        """Compresse un fichier selon son type"""
        extension = input_path.suffix.lower()
        
        if extension in self.image_extensions:
            return self.compress_image(input_path, **kwargs)
        elif extension in self.pdf_extensions:
            return self.compress_pdf(input_path)
        elif extension in self.video_extensions:
            return self.compress_video(input_path, **kwargs)
        elif extension in self.audio_extensions:
            return self.compress_audio(input_path, **kwargs)
        else:
            print(f"Type de fichier non supporté: {extension}")
            return None
    
    def compress_directory(self, input_dir: Path, **kwargs) -> None:
        """Compresse tous les fichiers supportés dans un répertoire"""
        supported_extensions = (
            self.image_extensions | self.pdf_extensions | 
            self.video_extensions | self.audio_extensions
        )
        
        files_to_compress = []
        for ext in supported_extensions:
            files_to_compress.extend(input_dir.rglob(f"*{ext}"))
        
        if not files_to_compress:
            print("Aucun fichier supporté trouvé dans le répertoire.")
            return
        
        print(f"Trouvé {len(files_to_compress)} fichier(s) à compresser...")
        
        total_original_size = 0
        total_compressed_size = 0
        successful_compressions = 0
        
        for file_path in files_to_compress:
            print(f"\nCompression de: {file_path.name}")
            original_size = self.get_file_size(file_path)
            total_original_size += original_size
            
            output_path = self.compress_file(file_path, **kwargs)
            
            if output_path and output_path.exists():
                compressed_size = self.get_file_size(output_path)
                total_compressed_size += compressed_size
                successful_compressions += 1
                
                compression_ratio = (1 - compressed_size / original_size) * 100
                print(f"✓ Compressé: {self.format_size(original_size)} → {self.format_size(compressed_size)} ({compression_ratio:.1f}% de réduction)")
            else:
                print("✗ Échec de la compression")
        
        # Statistiques finales
        if successful_compressions > 0:
            total_compression_ratio = (1 - total_compressed_size / total_original_size) * 100
            print(f"\n{'='*50}")
            print(f"RÉSUMÉ DE LA COMPRESSION:")
            print(f"Fichiers traités: {successful_compressions}/{len(files_to_compress)}")
            print(f"Taille originale totale: {self.format_size(total_original_size)}")
            print(f"Taille compressée totale: {self.format_size(total_compressed_size)}")
            print(f"Réduction totale: {self.format_size(total_original_size - total_compressed_size)} ({total_compression_ratio:.1f}%)")
            print(f"Fichiers sauvegardés dans: {self.output_dir}")


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Compresseur de fichiers multimédia")
    parser.add_argument("input", help="Fichier ou répertoire à compresser")
    parser.add_argument("-o", "--output", default="compressed", help="Répertoire de sortie (défaut: compressed)")
    parser.add_argument("-q", "--quality", type=int, default=85, help="Qualité pour images (1-100, défaut: 85)")
    parser.add_argument("--video-bitrate", default="1000k", help="Bitrate vidéo (défaut: 1000k)")
    parser.add_argument("--audio-bitrate", default="128k", help="Bitrate audio (défaut: 128k)")
    parser.add_argument("--max-width", type=int, default=1920, help="Largeur max pour images/vidéos (défaut: 1920)")
    parser.add_argument("--max-height", type=int, default=1080, help="Hauteur max pour images/vidéos (défaut: 1080)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Erreur: Le fichier ou répertoire '{args.input}' n'existe pas.")
        sys.exit(1)
    
    # Créer le compresseur
    compressor = FileCompressor(args.output)
    
    # Paramètres de compression
    compression_params = {
        'quality': args.quality,
        'bitrate': args.video_bitrate,
        'max_resolution': (args.max_width, args.max_height)
    }
    
    # Compresser
    if input_path.is_file():
        print(f"Compression du fichier: {input_path}")
        original_size = compressor.get_file_size(input_path)
        
        output_path = compressor.compress_file(input_path, **compression_params)
        
        if output_path and output_path.exists():
            compressed_size = compressor.get_file_size(output_path)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            print(f"\n✓ Compression réussie!")
            print(f"Taille originale: {compressor.format_size(original_size)}")
            print(f"Taille compressée: {compressor.format_size(compressed_size)}")
            print(f"Réduction: {compression_ratio:.1f}%")
            print(f"Fichier sauvegardé: {output_path}")
        else:
            print("✗ Échec de la compression")
            
    elif input_path.is_dir():
        print(f"Compression du répertoire: {input_path}")
        compressor.compress_directory(input_path, **compression_params)
    
    else:
        print("Erreur: L'entrée n'est ni un fichier ni un répertoire valide.")
        sys.exit(1)


if __name__ == "__main__":
    main()