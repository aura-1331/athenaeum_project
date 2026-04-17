export interface BookDetails {
  id: number;
  serial_no: number;
  accession_no: string;
  title: string;
  author: string;
  language_id: string; // From items table
  category: string;
  original_language?: string;
  translation_compilation?: string | null;
  genre: string | null;
  ddc: string;
  call_no: string | null; // From items table
  isbn: string;
  shelf: string | null; // From items table
  publisher: string;
  year: number;         // Integer in DB
  notes?: string | null;
  work_id: number;
}