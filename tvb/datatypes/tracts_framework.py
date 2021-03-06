# -*- coding: utf-8 -*-
#
#
# TheVirtualBrain-Framework Package. This package holds all Data Management, and 
# Web-UI helpful to run brain-simulations. To use it, you also need do download
# TheVirtualBrain-Scientific Package (for simulators). See content of the
# documentation-folder for more details. See also http://www.thevirtualbrain.org
#
# (c) 2012-2013, Baycrest Centre for Geriatric Care ("Baycrest")
#
# This program is free software; you can redistribute it and/or modify it under 
# the terms of the GNU General Public License version 2 as published by the Free
# Software Foundation. This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
# License for more details. You should have received a copy of the GNU General 
# Public License along with this program; if not, you can download it here
# http://www.gnu.org/licenses/old-licenses/gpl-2.0
#
#
# CITATION:
# When using The Virtual Brain for scientific publications, please cite it as follows:
#
#   Paula Sanz Leon, Stuart A. Knock, M. Marmaduke Woodman, Lia Domide,
#   Jochen Mersmann, Anthony R. McIntosh, Viktor Jirsa (2013)
#       The Virtual Brain: a simulator of primate brain network dynamics.
#   Frontiers in Neuroinformatics (7:10. doi: 10.3389/fninf.2013.00010)
#
#

"""
module docstring
.. moduleauthor:: Mihai Andrei <mihai.andrei@codemart.ro>
"""
import numpy
from tvb.basic.logger.builder import get_logger
from tvb.datatypes.tracts_data import TractData

LOG = get_logger(__name__)

TRACTS_CHUNK_SIZE = 100

class TractsFramework(TractData):
    __tablename__ = None

    MAX_UINT16 = 2**16

    def get_tract(self, i):
        """
        get a tract by index
        """
        start, end = self.tract_start_idx[i:i+2]
        return self.get_data('vertices', slice(start, end), close_file=False)


    def _get_tract_ids(self, region_id):
        tract_ids = numpy.where(self.tract_region == region_id)[0]
        return tract_ids


    def _get_track_ids_webgl_chunks(self, region_id):
        """
        webgl can draw up to MAX_UINT16 vertices in a draw call.
        Assuming that no one track exceeds this limit we partition
        the tracts such that each track bundle has fewer than the max vertices
        :return: the id's of the tracts in a region chunked by the above criteria.
        """
        # We have to split the int64 range in many uint16 ranges
        tract_ids = self._get_tract_ids(region_id)

        tract_id_chunks = []
        chunk = []

        count = 0
        tidx = 0
        tract_start_idx = self.tract_start_idx # traits make . expensive

        while tidx < len(tract_ids):  # tidx always grows
            tid = tract_ids[tidx]
            start, end = tract_start_idx[tid:tid+2]
            track_len = end - start

            if track_len >= self.MAX_UINT16:
                raise ValueError('cannot yet handle very long tracts')

            count += track_len

            if count < self.MAX_UINT16:
                # add this track to the current chunk and advance to next track
                chunk.append(tid)
                tidx += 1
            else:
                # stay with the same track and start a new chunk
                tract_id_chunks.append(chunk)
                chunk = []
                count = 0

        if chunk:
            tract_id_chunks.append(chunk)

        # q = []
        # for a in tract_id_chunks:
        #     q.extend(a)
        # assert (numpy.array(q) == tract_ids).all()

        return tract_id_chunks


    def get_vertices(self, region_id, slice_number=0):
        """
        Concatenates the vertices for all tracts starting in region_id.
        Returns a completely flat array as required by gl.bindBuffer apis
        """
        region_id = int(region_id)
        slice_number = int(slice_number)

        chunks = self._get_track_ids_webgl_chunks(region_id)
        tract_ids = chunks[slice_number]

        tracts_vertices = []
        for tid in tract_ids:
            tracts_vertices.append(self.get_tract(tid))

        self.close_file()

        if tracts_vertices:
            tracts_vertices = numpy.concatenate(tracts_vertices)
            return tracts_vertices.ravel()
        else:
            return numpy.array([])


    def get_line_starts(self, region_id):
        """
        Returns a compact representation of the element buffers required to draw the streams via gl.drawElements
        A list of indices that describe where the first vertex for a tract is in the vertex array returned by
        get_tract_vertices_starting_in_region
        """
        region_id = int(region_id)
        chunks = self._get_track_ids_webgl_chunks(region_id)
        chunk_line_starts = []
        tract_start_idx = self.tract_start_idx # traits make the . expensive

        for tract_ids in chunks:
            offset = 0
            tract_offsets = [0]

            for tid in tract_ids:
                start, end = tract_start_idx[tid:tid+2]
                track_len = end - start
                offset +=track_len
                tract_offsets.append(offset)

            chunk_line_starts.append(tract_offsets)

        return chunk_line_starts


    def get_urls_for_rendering(self):
        return ('/flow/read_datatype_attribute/'+self.gid+'/get_line_starts/False',
                '/flow/read_binary_datatype_attribute/' + self.gid + '/get_vertices')