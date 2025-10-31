/**
 * Training Summary Cards Utilities
 * Client-side calculations for training summary metrics
 * Fixed to match server-side callback logic exactly - CORRECTED DATE FILTERING
 */

class TrainingSummaryUtils {
    
    /**
     * Parse filter string into array of clean values
     * @param {string} filterStr - Filter string like "'AOR1', 'AOR2'"
     * @returns {Array} Array of clean filter values
     */
    static parseFilterList(filterStr) {
        if (!filterStr) return [];
        return filterStr.split(', ')
            .map(item => item.replace(/'/g, '').trim())
            .filter(item => item);
    }
    
    /**
     * Parse custom datetime format: "Feb-04-25@6 PM"
     * @param {string} dateStr - Date string in custom format
     * @returns {Date|null} Parsed date object or null
     */
    static parseCustomDateTime(dateStr) {
        if (!dateStr) return null;
        
        try {
            // console.log('🔍 Parsing custom date string:', dateStr);
            if (dateStr.includes('@')) {
                const [datePart, timePart] = dateStr.split('@');
                const [month, day, year] = datePart.split('-');
                const fullYear = year.length === 2 ? '20' + year : year;
                
                // Fix the time format - convert "4 PM" to "4:00 PM"
                let formattedTime = timePart.trim();
                
                // If time doesn't have colon (like "4 PM"), add ":00"
                if (!formattedTime.includes(':')) {
                    // Split by space to separate hour and AM/PM
                    const timeParts = formattedTime.split(' ');
                    if (timeParts.length === 2) {
                        const hour = timeParts[0];
                        const period = timeParts[1];
                        formattedTime = `${hour}:00 ${period}`;
                    }
                }
                
                const dateString = `${month} ${day} ${fullYear} ${formattedTime}`;
                // console.log('🔍 Constructed date string for parsing:', dateString);
                
                const parsedDate = new Date(dateString);
                // console.log('📅 Parsed date object:', parsedDate);
                // console.log('📅 Is valid date?', !isNaN(parsedDate.getTime()));
                
                return !isNaN(parsedDate.getTime()) ? parsedDate : null;
            }
            return new Date(dateStr);
        } catch (e) {
            console.warn('⚠️ Error parsing date:', dateStr, e);
            return null;
        }
    }
    
    /**
     * Filter classes based on query selections - FIXED to match server-side logic exactly
     * @param {Array} classes - Classes data array
     * @param {Object} selections - Query selections object
     * @returns {Array} Filtered classes array
     */
    static filterClasses(classes, selections) {
        if (!Array.isArray(classes)) return [];
        
        let filtered = [...classes];
        
        if (!selections || typeof selections !== 'object') {
            // console.log('🔄 No query selections - returning all classes:', filtered.length);
            return filtered;
        }
        
        // Parse AOR filter
        const aors_filter = selections.AORs || '';
        const aor_list = this.parseFilterList(aors_filter);
        
        // Filter by AOR - only if AOR filter is present AND classes have AorShortName column
        if (aor_list.length > 0 && filtered.length > 0 && filtered[0].hasOwnProperty('AorShortName')) {
            filtered = filtered.filter(cls => 
                aor_list.includes(cls.AorShortName)
            );
            // console.log(`🎯 AOR filtering applied to CLASSES: ${filtered.length} classes for AORs: ${aor_list}`);
        }
        
        // Filter by date range - CRITICAL FIX: only if classes are not empty AND both dates are present AND classes have StartTime
        if (filtered.length > 0 && filtered[0].hasOwnProperty('StartTime')) {
            const start_date_str = selections.Day_From;
            const end_date_str = selections.Day_To;
            
            if (start_date_str && end_date_str) {
                // console.log('🔍 Parsing custom datetime format for classes...');
                
                const start_date = new Date(start_date_str);
                const end_date = new Date(end_date_str);
                
                // FIXED: First parse all dates, then filter out parsing failures, then apply date range
                const classesWithParsedDates = filtered.map(cls => ({
                    ...cls,
                    ParsedStartTime: this.parseCustomDateTime(cls.StartTime)
                }));
                
                // Filter out rows where parsing failed (matches server-side dropna)
                const classesWithValidDates = classesWithParsedDates.filter(cls => 
                    cls.ParsedStartTime !== null
                );
                
                // console.log(`📅 Classes before date parsing: ${filtered.length}, after parsing: ${classesWithValidDates.length}`);
                
                // Apply date range filter
                filtered = classesWithValidDates.filter(cls => {
                    return cls.ParsedStartTime >= start_date && cls.ParsedStartTime <= end_date;
                });
                
                // console.log(`📅 Date filtering applied to CLASSES: ${filtered.length} classes between ${start_date.toDateString()} and ${end_date.toDateString()}`);
            }
        }
        
        // Filter by Topics - only if topics filter is present AND classes have TopicId
        const topics_filter = selections.Topics || '';
        const topic_list = this.parseFilterList(topics_filter);
        
        if (topic_list.length > 0 && filtered.length > 0 && filtered[0].hasOwnProperty('TopicId')) {
            const topic_ids = topic_list.map(topic => String(topic));
            filtered = filtered.filter(cls => 
                topic_ids.includes(String(cls.TopicId))
            );
            // console.log(`📚 Topic filtering applied to CLASSES: ${filtered.length} classes for topics: ${topic_ids}`);
        }
        
        // Filter by Instructors - only if instructors filter is present AND classes have InstructorId
        const instructors_filter = selections.Instructors || '';
        const instructor_list = this.parseFilterList(instructors_filter);
        
        if (instructor_list.length > 0 && filtered.length > 0 && filtered[0].hasOwnProperty('InstructorId')) {
            const instructor_ids = instructor_list.map(inst => String(inst));
            filtered = filtered.filter(cls => 
                instructor_ids.includes(String(cls.InstructorId))
            );
            // console.log(`👨‍🏫 Instructor filtering applied to CLASSES: ${filtered.length} classes for instructors: ${instructor_ids}`);
        }
        
        // Filter by Locations - only if locations filter is present AND classes have LocationId
        const locations_filter = selections.Locations || '';
        const location_list = this.parseFilterList(locations_filter);
        
        if (location_list.length > 0 && filtered.length > 0 && filtered[0].hasOwnProperty('LocationId')) {
            const location_ids = location_list.map(loc => String(loc));
            filtered = filtered.filter(cls => 
                location_ids.includes(String(cls.LocationId))
            );
            // console.log(`📍 Location filtering applied to CLASSES: ${filtered.length} classes for locations: ${location_ids}`);
        }
        
        // console.log(`✅ Final filtered classes count: ${filtered.length}`);
        return filtered;
    }
    
    // ... rest of the methods remain the same ...
    
    /**
     * Filter attendance data based on query selections - matches server-side logic exactly
     */
    static filterAttendance(attendance, selections) {
        if (!Array.isArray(attendance)) return [];
        
        let filtered = [...attendance];
        
        if (!selections || typeof selections !== 'object') {
            return filtered;
        }
        
        // Parse filter values
        const aors_filter = selections.AORs || '';
        const aor_list = this.parseFilterList(aors_filter);
        
        const offices_filter = selections.Offices || '';
        const office_list = this.parseFilterList(offices_filter);
        
        const topics_filter = selections.Topics || '';
        const topic_list = this.parseFilterList(topics_filter);
        
        const instructors_filter = selections.Instructors || '';
        const instructor_list = this.parseFilterList(instructors_filter);
        
        const locations_filter = selections.Locations || '';
        const location_list = this.parseFilterList(locations_filter);
        
        // Apply filters only if they exist
        if (aor_list.length > 0) {
            filtered = filtered.filter(att => 
                aor_list.includes(att.AorShortName)
            );
            // console.log(`🎯 AOR filtering applied to ATTENDANCE: ${filtered.length} attendance records for AORs: ${aor_list}`);
        }
        
        if (office_list.length > 0) {
            filtered = filtered.filter(att => 
                office_list.includes(att.MemberOffice)
            );
            // console.log(`🏢 Office filtering applied to ATTENDANCE: ${filtered.length} attendance records for offices: ${office_list}`);
        }
        
        if (topic_list.length > 0) {
            const topic_ids = topic_list.map(topic => String(topic));
            filtered = filtered.filter(att => 
                topic_ids.includes(String(att.TrainingTopicId))
            );
            // console.log(`📚 Topic filtering applied to ATTENDANCE: ${filtered.length} attendance records for topics: ${topic_ids}`);
        }
        
        if (instructor_list.length > 0) {
            const instructor_ids = instructor_list.map(inst => String(inst));
            filtered = filtered.filter(att => 
                instructor_ids.includes(String(att.InstructorId))
            );
            // console.log(`👨‍🏫 Instructor filtering applied to ATTENDANCE: ${filtered.length} attendance records for instructors: ${instructor_ids}`);
        }
        
        if (location_list.length > 0) {
            const location_ids = location_list.map(loc => String(loc));
            filtered = filtered.filter(att => 
                location_ids.includes(String(att.LocationId))
            );
            // console.log(`📍 Location filtering applied to ATTENDANCE: ${filtered.length} attendance records for locations: ${location_ids}`);
        }
        
        return filtered;
    }
    
    /**
     * Filter requests data based on query selections - matches server-side logic exactly
     */
    static filterRequests(requests, selections) {
        if (!Array.isArray(requests) || requests.length === 0) return [];
        
        let filtered = [...requests];
        
        if (!selections || typeof selections !== 'object') {
            return filtered;
        }
        
        // Parse filter values
        const aors_filter = selections.AORs || '';
        const aor_list = this.parseFilterList(aors_filter);
        
        const offices_filter = selections.Offices || '';
        const office_list = this.parseFilterList(offices_filter);
        
        // Apply filters only if they exist
        if (aor_list.length > 0) {
            filtered = filtered.filter(req => 
                aor_list.includes(req.AorShortName)
            );
            // console.log(`🎯 AOR filtering applied to REQUESTS: ${filtered.length} request records`);
        }
        
        if (office_list.length > 0) {
            filtered = filtered.filter(req => 
                office_list.includes(req.MemberOffice)
            );
            // console.log(`🏢 Office filtering applied to REQUESTS: ${filtered.length} request records`);
        }
        
        return filtered;
    }
    
    /**
     * Filter active members with AOR-based office resolution - matches server-side logic exactly
     */
    static filterActiveMembers(activeMembers, offices, selections) {
        if (!Array.isArray(activeMembers)) return [];
        
        let filtered = [...activeMembers];
        
        if (!selections || typeof selections !== 'object') {
            return filtered;
        }
        
        // Parse filter values
        const aors_filter = selections.AORs || '';
        const aor_list = this.parseFilterList(aors_filter);
        
        const offices_filter = selections.Offices || '';
        const office_list = this.parseFilterList(offices_filter);
        
        // Determine which offices to filter by
        let offices_to_filter = [];
        
        if (office_list.length > 0) {
            // If specific offices are selected, use those
            offices_to_filter = office_list;
            // console.log('🏢 Using explicitly selected offices:', office_list);
        } else if (aor_list.length > 0) {
            // If AORs are selected but no specific offices, get all offices under those AORs
            if (Array.isArray(offices)) {
                const aor_offices = offices.filter(office => 
                    aor_list.includes(office.AorShortName)
                );
                offices_to_filter = [...new Set(aor_offices.map(office => office.OfficeCode))];
                // console.log(`🎯 AOR-based filtering: Found ${offices_to_filter.length} offices for AORs ${aor_list}`);
                // console.log('📋 Offices under selected AORs:', offices_to_filter);
            }
        }
        
        // Apply office filtering only if we have offices to filter by
        if (offices_to_filter.length > 0) {
            filtered = filtered.filter(member => 
                offices_to_filter.includes(member.OfficeCode)
            );
            // console.log(`🏢 Office filtering applied to ACTIVE MEMBERS: ${filtered.length} members for offices: ${offices_to_filter}`);
        }
        
        return filtered;
    }
    
    /**
     * Calculate summary metrics from filtered data - matches server-side logic exactly
     */
    static calculateMetrics(classes, attendance, requests, activeMembers) {
        const metrics = {
            totalClasses: 0,
            totalAttendances: 0,
            totalRequests: 0,
            activeMembers: 0
        };
        
        try {
            // 1. Total Classes
            metrics.totalClasses = Array.isArray(classes) ? classes.length : 0;
            
            // 2. Total Attendances - sum TotalAttendances column or fallback to count
            if (Array.isArray(attendance)) {
                if (attendance.length > 0 && attendance[0].hasOwnProperty('TotalAttendances')) {
                    metrics.totalAttendances = attendance.reduce((sum, att) => 
                        sum + (parseInt(att.TotalAttendances) || 0), 0
                    );
                } else {
                    // Fallback: count attendance records
                    metrics.totalAttendances = attendance.length;
                }
            }
            
            // 3. Total Requests - sum TotalRequests column or fallback to count
            if (Array.isArray(requests)) {
                if (requests.length > 0 && requests[0].hasOwnProperty('TotalRequests')) {
                    metrics.totalRequests = requests.reduce((sum, req) => 
                        sum + (parseInt(req.TotalRequests) || 0), 0
                    );
                } else {
                    // Fallback: count request records
                    metrics.totalRequests = requests.length;
                }
            }
            
            // 4. Active Members - count unique MemberIDs
            if (Array.isArray(activeMembers)) {
                const uniqueMembers = new Set(activeMembers.map(member => member.MemberID));
                metrics.activeMembers = uniqueMembers.size;
            }
            
        } catch (error) {
            console.error('❌ Error calculating metrics:', error);
        }
        
        return metrics;
    }
    
    /**
     * Format metrics for display
     */
    static formatMetrics(metrics) {
        const formatNumber = (num) => num.toLocaleString();
        
        return [
            formatNumber(metrics.totalClasses),
            formatNumber(metrics.totalAttendances),
            formatNumber(metrics.totalRequests),
            formatNumber(metrics.activeMembers)
        ];
    }
    
    /**
     * Main function to update summary cards - called by client-side callback
     * Matches server-side callback logic exactly
     */
    static updateSummaryCards(filtered_data, query_selections) {
        // console.log('🔄 TrainingSummaryUtils: Client-side summary update triggered');
        
        if (!filtered_data || typeof filtered_data !== 'object') {
            // console.log('⚠️ No filtered data available');
            return ["0", "0", "0", "0"];
        }
        
        try {
            // Extract data arrays - exactly as server-side does
            const classes_data = filtered_data.classes || [];
            const attendance_data = filtered_data.attendance_stats || [];
            const request_data = filtered_data.request_stats || [];
            const active_members_data = filtered_data.active_members || [];
            const offices_data = filtered_data.offices || [];
            
            // console.log('📊 Initial Data counts:', {
            //     classes: classes_data.length,
            //     attendance: attendance_data.length,
            //     requests: request_data.length,
            //     activeMembers: active_members_data.length,
            //     offices: offices_data.length
            // });
            
            const selections = query_selections || {};
            
            // console.log('📋 Query Selections:', selections);
            
            // Filter all data types - exactly matching server-side logic
            const filtered_classes = this.filterClasses(classes_data, selections);
            const filtered_attendance = this.filterAttendance(attendance_data, selections);
            const filtered_requests = this.filterRequests(request_data, selections);
            const filtered_active_members = this.filterActiveMembers(
                active_members_data, 
                offices_data, 
                selections
            );
            
            // console.log('📊 Final Filtered data counts:', {
            //     classes: filtered_classes.length,
            //     attendance: filtered_attendance.length,
            //     requests: filtered_requests.length,
            //     activeMembers: filtered_active_members.length
            // });
            
            // Calculate metrics
            const metrics = this.calculateMetrics(
                filtered_classes,
                filtered_attendance,
                filtered_requests,
                filtered_active_members
            );
            
            // console.log(`📊 TrainingSummaryUtils: Summary Updated - Classes=${metrics.totalClasses}, Attendances=${metrics.totalAttendances}, Requests=${metrics.totalRequests}, Members=${metrics.activeMembers}`);
            
            // Format and return results
            return this.formatMetrics(metrics);
            
        } catch (error) {
            console.error('❌ Error in TrainingSummaryUtils.updateSummaryCards:', error);
            return ["0", "0", "0", "0"];
        }
    }
}

// Make globally available
window.TrainingSummaryUtils = TrainingSummaryUtils;