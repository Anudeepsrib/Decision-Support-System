import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { MappingService } from '../../services/api';
import { MappingSuggestion, MappingStatus, VarianceCategory, CostHead } from '../../services/types';

export function MappingWorkbench() {
  const [mappings, setMappings] = useState<MappingSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMapping, setSelectedMapping] = useState<MappingSuggestion | null>(null);
  const [comment, setComment] = useState('');
  const [overrideHead, setOverrideHead] = useState('');
  const [overrideCategory, setOverrideCategory] = useState<VarianceCategory>(VarianceCategory.CONTROLLABLE);

  useEffect(() => {
    loadPendingMappings();
  }, []);

  const loadPendingMappings = async () => {
    try {
      setLoading(true);
      const data = await MappingService.getPendingMappings();
      setMappings(data);
    } catch (error) {
      toast.error('Failed to load pending mappings');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (mapping: MappingSuggestion) => {
    if (!comment.trim()) {
      toast.error('Please provide a comment');
      return;
    }

    try {
      await MappingService.confirmMapping({
        mapping_id: mapping.mapping_id,
        decision: 'Confirmed',
        comment,
        officer_name: 'Current User',
      });
      toast.success('Mapping confirmed');
      setComment('');
      setSelectedMapping(null);
      loadPendingMappings();
    } catch (error) {
      toast.error('Failed to confirm mapping');
    }
  };

  const handleOverride = async (mapping: MappingSuggestion) => {
    if (!comment.trim() || !overrideHead.trim()) {
      toast.error('Please provide a comment and override category');
      return;
    }

    try {
      await MappingService.overrideMapping(
        mapping.mapping_id,
        overrideHead,
        overrideCategory,
        comment
      );
      toast.success('Mapping overridden');
      setComment('');
      setOverrideHead('');
      setSelectedMapping(null);
      loadPendingMappings();
    } catch (error) {
      toast.error('Failed to override mapping');
    }
  };

  const handleReject = async (mapping: MappingSuggestion) => {
    if (!comment.trim()) {
      toast.error('Please provide a reason for rejection');
      return;
    }

    try {
      await MappingService.rejectMapping(mapping.mapping_id, comment);
      toast.success('Mapping rejected');
      setComment('');
      setSelectedMapping(null);
      loadPendingMappings();
    } catch (error) {
      toast.error('Failed to reject mapping');
    }
  };

  if (loading) {
    return <div className="p-4">Loading pending mappings...</div>;
  }

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Mapping Workbench</h2>
      <p className="text-gray-600 mb-4">
        Review and verify AI-suggested mappings before they enter the Rule Engine.
      </p>

      {mappings.length === 0 ? (
        <div className="text-green-600">No pending mappings. All caught up!</div>
      ) : (
        <div className="space-y-4">
          {mappings.map((mapping) => (
            <div
              key={mapping.mapping_id}
              className={`border rounded-lg p-4 ${
                selectedMapping?.mapping_id === mapping.mapping_id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="inline-block px-2 py-1 text-xs font-semibold rounded bg-gray-100 mr-2">
                    {mapping.sbu_code}
                  </span>
                  <span className="font-medium">{mapping.source_field}</span>
                </div>
                <span className="text-sm text-gray-500">
                  Confidence: {(mapping.confidence * 100).toFixed(0)}%
                </span>
              </div>

              <div className="mb-3">
                <p className="text-sm text-gray-600">
                  AI suggests: <strong>{mapping.suggested_head}</strong> (
                  {mapping.suggested_category})
                </p>
                <p className="text-sm text-gray-500 mt-1">{mapping.reasoning}</p>
              </div>

              {selectedMapping?.mapping_id === mapping.mapping_id ? (
                <div className="mt-4 space-y-3">
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Add your comment (required)..."
                    className="w-full p-2 border rounded"
                    rows={3}
                  />

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleConfirm(mapping)}
                      className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                    >
                      ✅ Confirm
                    </button>
                    <button
                      onClick={() => setSelectedMapping(null)}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setSelectedMapping(mapping)}
                  className="text-blue-500 hover:text-blue-700 text-sm"
                >
                  Review →
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
