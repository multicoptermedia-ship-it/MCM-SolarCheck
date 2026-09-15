"""Structural parser for DJI Mavic 3 Thermal radiometric JPEG/MPO files.

The validated M3T radiometric stream contains APP3 raw samples followed by
APP4/APP5 auxiliary data. Raw 16-bit samples are exposed without claiming a
Celsius conversion.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import struct
APP3=0xE3;APP4=0xE4;APP5=0xE5
@dataclass(frozen=True)
class JpegSegment:
    marker:int;offset:int;payload:bytes
@dataclass(frozen=True)
class RadiometricRaster:
    width:int;height:int;byte_order:str;samples:tuple[int,...];stream_offset:int
    @property
    def pixel_count(self)->int:return self.width*self.height
class M3TFormatError(ValueError):pass
class M3TRadiometricParser:
    width=640;height=512;bytes_per_sample=2;full_app3_payload_size=65532
    @property
    def expected_payload_size(self)->int:return self.width*self.height*self.bytes_per_sample
    def parse_file(self,path:str|Path)->RadiometricRaster:return self.parse_bytes(Path(path).read_bytes())
    def parse_bytes(self,data:bytes)->RadiometricRaster:
        segments=self.radiometric_segments(data);payload=b''.join(s.payload for s in segments if s.marker==APP3)
        if len(payload)!=self.expected_payload_size:raise M3TFormatError(f'Expected {self.expected_payload_size} radiometric APP3 bytes, observed {len(payload)}')
        samples=struct.unpack(f'<{self.width*self.height}H',payload)
        return RadiometricRaster(self.width,self.height,'little',samples,segments[0].offset)
    def auxiliary_blocks(self,data:bytes)->dict[int,tuple[bytes,...]]:
        result={APP4:[],APP5:[]}
        for segment in self.radiometric_segments(data):
            if segment.marker in result:result[segment.marker].append(segment.payload)
        return {marker:tuple(parts) for marker,parts in result.items()}
    def radiometric_segments(self,data:bytes)->tuple[JpegSegment,...]:
        signature=b'\xff\xe3\xff\xfe';starts=[];pos=0
        while True:
            pos=data.find(signature,pos)
            if pos<0:break
            starts.append(pos);pos+=1
        candidates=[]
        for start in starts:
            try:chain=self._parse_app_chain(data,start)
            except M3TFormatError:continue
            app3=[s for s in chain if s.marker==APP3];app4=[s for s in chain if s.marker==APP4];app5=[s for s in chain if s.marker==APP5]
            if sum(len(s.payload) for s in app3)==self.expected_payload_size and len(app4)==1 and len(app4[0].payload)==256 and len(app5)==1 and len(app5[0].payload)==23818:candidates.append(chain)
        if not candidates:raise M3TFormatError('No validated M3T radiometric APP stream found')
        candidates.sort(key=lambda c:c[0].offset);return candidates[0]
    @staticmethod
    def _parse_app_chain(data:bytes,start:int)->tuple[JpegSegment,...]:
        """Parse only the radiometric APP3→APP4→APP5 chain.

        APP5 is the validated terminal block. Bytes after it belong to other
        container data and must not be allowed to invalidate an already complete
        radiometric stream, even when they contain an FF E3 byte sequence.
        """
        segments=[];i=start;n=len(data)
        while i+4<=n and data[i]==0xFF and 0xE0<=data[i+1]<=0xEF:
            marker=data[i+1];length=int.from_bytes(data[i+2:i+4],'big')
            if length<2:raise M3TFormatError(f'Invalid APP segment length {length}')
            end=i+2+length
            if end>n:raise M3TFormatError('APP segment extends beyond file')
            segments.append(JpegSegment(marker,i,data[i+4:end]));i=end
            if marker==APP5:break
        return tuple(segments)
