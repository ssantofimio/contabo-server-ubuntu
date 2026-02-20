# -*- coding: utf-8 -*-
###############################################################################
#
#  Cybrosys Technologies Pvt. Ltd.
#
#  Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#  Author: Jumana Haseen (odoo@cybrosys.com)
#
#  You can modify it under the terms of the GNU LESSER
#  GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#  You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#  (LGPL v3) along with this program.
#  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import json
from odoo.http import content_disposition, request
from odoo import http
from odoo.tools import html_escape
import logging

_logger = logging.getLogger(__name__)


class XLSXReportController(http.Controller):
    """ This model is used to connect the frontend to the backend """
    @http.route('/xlsx_reports', type='http', auth='user',
                methods=['GET', 'POST'], csrf=False)
    def get_report_xlsx(self, **kwargs):
        """This function is called when a request is made to this route"""
        _logger.info("XLSXReportController: Request received with params %s", kwargs)
        
        model = kwargs.get('model')
        options_raw = kwargs.get('options')
        output_format = kwargs.get('output_format', 'xlsx')
        report_name = kwargs.get('report_name', 'Reporte')

        if not model or not options_raw:
            _logger.error("XLSXReportController: Missing model or options")
            return request.make_response("Missing parameters", status=400)

        uid = request.session.uid
        report_obj = request.env[model].with_user(uid)
        
        try:
            options = json.loads(options_raw)
        except Exception as e:
            _logger.error("XLSXReportController: Error parsing options: %s", str(e))
            return request.make_response("Invalid options JSON", status=400)

        token = 'dummy-token'
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition',
                         content_disposition(report_name + '.xlsx'))
                    ])
                report_obj.get_xlsx_report(options, response)
                response.set_cookie('fileToken', token)
                _logger.info("XLSXReportController: Report generated successfully")
                return response
        except Exception as e:
            _logger.error("XLSXReportController Error during generation: %s", str(e), exc_info=True)
            serialise = http.serialize_exception(e)
            error = {
                'code': 500,
                'message': 'Odoo Server Error during XLSX generation',
                'data': serialise
            }
            return request.make_response(html_escape(json.dumps(error)), status=500)
        
        return request.make_response("Unknown error", status=500)
