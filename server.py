#!/usr/bin/env python3
"""VELOCE — Auto eléctrico. Concepto Hilo Rojo (ibuongiorno). Servidor con Range."""
import http.server, socketserver, os, re

PORT = 8907
DIR = '/root/web-veloce'

class H(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # NECESARIO: HTTP/1.0 rompe streaming vía proxy HTTP/2

    def __init__(self, *a, **kw):
        # CRÍTICO: socketserver.__init__ procesa la 1ª petición dentro del constructor
        self._range_length = None
        super().__init__(*a, directory=DIR, **kw)

    def log_message(self, *a):
        pass

    def send_head(self):
        """Soporte Range: 206 Partial Content para streaming de video."""
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()

        size = os.path.getsize(path)
        ctype = self.guess_type(path)
        range_header = self.headers.get('Range')
        self._range_length = None

        if range_header:
            m = re.match(r'bytes=(\d*)-(\d*)', range_header)
            if m:
                start = int(m.group(1)) if m.group(1) else 0
                end = int(m.group(2)) if m.group(2) else size - 1
                end = min(end, size - 1)
                if start <= end:
                    length = end - start + 1
                    self._range_length = length
                    self.send_response(206)
                    self.send_header('Content-Type', ctype)
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                    self.send_header('Content-Length', str(length))
                    self.send_header('Last-Modified', self.date_time_string(os.path.getmtime(path)))
                    self.end_headers()
                    f = open(path, 'rb')
                    f.seek(start)
                    return f

        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(size))
        self.send_header('Last-Modified', self.date_time_string(os.path.getmtime(path)))
        self.end_headers()
        return open(path, 'rb')

    def copyfile(self, source, outputfile):
        if self._range_length is not None:
            remaining = self._range_length
            while remaining > 0:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        else:
            super().copyfile(source, outputfile)

if __name__ == '__main__':
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('0.0.0.0', PORT), H) as s:
        print(f'veloce en :{PORT} (Range OK)')
        s.serve_forever()
